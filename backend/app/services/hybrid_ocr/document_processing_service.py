"""업로드부터 OCR 결과 응답까지 Hybrid OCR 전체 순서를 관리합니다."""

import asyncio
import logging
from collections.abc import Callable

from fastapi import UploadFile

from app.core.config import settings
from app.schemas.admin import OcrDocumentResponse
from app.services.hybrid_ocr.chunk_service import create_chunks
from app.services.hybrid_ocr.document_validator import (
    validate_chunk_options,
    validate_document,
)
from app.services.hybrid_ocr.errors import DocumentProcessingError
from app.services.hybrid_ocr.image_preprocessor import preprocess_image
from app.services.hybrid_ocr.models import (
    ExtractedDocument,
    OcrEngine,
    OcrProcessingConfig,
    ProgressCallback,
    ValidatedDocument,
)
from app.services.hybrid_ocr.office_parser_service import (
    DirectOfficeDocumentParser,
    OfficeDocumentParser,
)
from app.services.hybrid_ocr.paddle_ocr_service import get_paddle_ocr_service
from app.services.hybrid_ocr.pdf_parser_service import process_pdf_document
from app.services.hybrid_ocr.text_cleaner import clean_document_text

logger = logging.getLogger(__name__)

DOCUMENT_TYPE_LABELS = {
    "image": "이미지",
    "digital_pdf": "디지털 PDF",
    "hybrid_pdf": "Hybrid PDF",
    "scanned_pdf": "스캔 PDF",
    "docx_direct": "DOCX 직접 추출",
    "pptx_direct": "PPTX 직접 추출",
}


class DocumentProcessingService:
    """세부 모듈의 결과를 되돌려 받아 다음 단계를 호출하는 중심 Service입니다."""

    def __init__(
        self,
        config: OcrProcessingConfig,
        ocr_service_factory: Callable[[], OcrEngine],
        office_parser: OfficeDocumentParser | None = None,
    ) -> None:
        self.config = config
        self.ocr_service_factory = ocr_service_factory
        self.office_parser = office_parser or DirectOfficeDocumentParser()

    async def process_document(
        self,
        file: UploadFile,
        chunk_size: int,
        overlap: int,
        progress_callback: ProgressCallback | None = None,
    ) -> OcrDocumentResponse:
        """검증 → 형식별 추출 → 정제 → Chunking → 응답의 순서를 관리합니다."""

        logger.info("Hybrid OCR 시작: filename=%s", file.filename)

        # 1. 업로드 파일과 Chunk 설정을 검증해 안전한 문서 데이터를 반환받습니다.
        _report_progress(progress_callback, "validating", 8, "업로드 파일을 검증하고 있습니다.")
        validate_chunk_options(chunk_size, overlap)
        validated_document = await validate_document(file, self.config)
        _report_progress(progress_callback, "validating", 15, "파일 검증이 완료되었습니다.")
        logger.info(
            "파일 검증 완료: filename=%s, type=%s, bytes=%d",
            validated_document.file_name,
            validated_document.file_type,
            len(validated_document.content),
        )

        # 2. 이미지/PDF/Office 형식에 맞는 처리 함수에 위임하고 공통 결과로 복귀합니다.
        _report_progress(progress_callback, "analyzing", 20, "문서 구조를 분석하고 있습니다.")
        extracted_document = await asyncio.to_thread(
            self._extract_document,
            validated_document,
            progress_callback,
        )
        _report_progress(progress_callback, "merging", 82, "문서 추출 결과를 통합했습니다.")
        logger.info(
            "문서 추출 완료: type=%s, pages=%s, ocr_images=%d",
            extracted_document.document_type,
            extracted_document.page_count,
            extracted_document.ocr_image_count,
        )

        # 3. 원문 의미는 유지하면서 RAG 입력에 불필요한 공백과 제어문자를 정리합니다.
        _report_progress(progress_callback, "cleaning", 86, "추출 텍스트를 정제하고 있습니다.")
        cleaned_text = clean_document_text(extracted_document.text)
        _report_progress(progress_callback, "cleaning", 90, "텍스트 정제가 완료되었습니다.")

        # 4. 관리자가 실제 분할 결과를 확인할 수 있도록 Chunk를 생성합니다.
        _report_progress(progress_callback, "chunking", 93, "RAG 검토용 Chunk를 생성하고 있습니다.")
        chunks = create_chunks(cleaned_text, chunk_size, overlap)
        _report_progress(progress_callback, "chunking", 97, f"Chunk {len(chunks)}개를 생성했습니다.")
        logger.info("Chunk 생성 완료: count=%d", len(chunks))

        # 5. 기존 Frontend 계약에 맞춘 응답을 조립해 Router로 반환합니다.
        response = self._build_response(
            validated_document,
            extracted_document,
            cleaned_text,
            chunks,
        )
        _report_progress(progress_callback, "finalizing", 99, "분석 결과를 구성했습니다.")
        logger.info("Hybrid OCR 완료: filename=%s", validated_document.file_name)
        return response

    def _extract_document(
        self,
        document: ValidatedDocument,
        progress_callback: ProgressCallback | None,
    ) -> ExtractedDocument:
        if document.file_type == "image":
            return self._process_image_document(document, progress_callback)
        if document.file_type == "pdf":
            return process_pdf_document(
                document.content,
                self.config,
                self.ocr_service_factory,
                progress_callback,
            )
        return self._process_office_document(document, progress_callback)

    def _process_office_document(
        self,
        document: ValidatedDocument,
        progress_callback: ProgressCallback | None,
    ) -> ExtractedDocument:
        """DOCX/PPTX의 OOXML 구조를 직접 읽고 포함 이미지만 OCR합니다."""

        _report_progress(
            progress_callback,
            "parsing_office",
            22,
            f"{document.file_type.upper()} 문서 구조를 직접 분석하고 있습니다.",
        )
        parsed = self.office_parser.parse(document)
        _report_progress(
            progress_callback,
            "parsing_office",
            35,
            "Office 문서의 텍스트와 이미지 구조를 확인했습니다.",
        )

        unit_texts: list[str] = []
        warnings = list(parsed.warnings)
        confidences: list[float] = []
        ocr_image_count = 0
        total_images = sum(len(unit.images) for unit in parsed.units)
        processed_images = 0

        for unit in parsed.units:
            unit_parts = [f"## {unit.title}"]
            if unit.text:
                unit_parts.append(unit.text)

            for image_index, image in enumerate(unit.images, start=1):
                progress = 35
                if total_images:
                    progress += round(processed_images / total_images * 45)
                processed_images += 1
                try:
                    processed = preprocess_image(
                        image.content,
                        self.config.max_image_side,
                        self.config.max_image_pixels,
                    )
                    if processed.width * processed.height < 4_096:
                        warnings.append(f"{image.label}가 너무 작아 OCR에서 제외했습니다.")
                        continue

                    _report_progress(
                        progress_callback,
                        "loading_model",
                        progress,
                        f"{image.label}의 텍스트를 OCR하고 있습니다.",
                    )
                    ocr_result = self.ocr_service_factory().extract_text(processed)
                    ocr_image_count += 1
                    if ocr_result.line_count:
                        confidences.append(ocr_result.confidence)
                    if ocr_result.text:
                        unit_parts.append(
                            f"### 이미지 OCR {image_index}\n\n{ocr_result.text.strip()}"
                        )
                    else:
                        warnings.append(f"{image.label}에서 텍스트를 찾지 못했습니다.")
                except DocumentProcessingError as exc:
                    warnings.append(f"{image.label} OCR을 건너뛰었습니다: {exc}")

            if len(unit_parts) > 1:
                unit_texts.append("\n\n".join(unit_parts))

        extracted_text = "\n\n".join(unit_texts)
        average_confidence = (
            sum(confidences) / len(confidences)
            if confidences
            else (1.0 if extracted_text else 0.0)
        )
        _report_progress(
            progress_callback,
            "extracting",
            80,
            "Office 문서의 직접 추출을 완료했습니다.",
        )
        return ExtractedDocument(
            text=extracted_text,
            page_count=parsed.page_count,
            document_type=parsed.document_type,
            ocr_image_count=ocr_image_count,
            average_confidence=average_confidence,
            warnings=warnings,
        )

    def _process_image_document(
        self,
        document: ValidatedDocument,
        progress_callback: ProgressCallback | None,
    ) -> ExtractedDocument:
        """일반 이미지를 로드·전처리한 뒤 PaddleOCR 결과를 반환받습니다."""

        # 1. EXIF 방향과 투명 배경, 최대 크기를 OCR에 적합하게 정리합니다.
        _report_progress(progress_callback, "preprocessing", 28, "OCR용 이미지를 전처리하고 있습니다.")
        processed_image = preprocess_image(
            document.content,
            self.config.max_image_side,
            self.config.max_image_pixels,
        )

        # 2. PaddleOCR에 이미지를 전달하고 단순화된 텍스트/신뢰도를 반환받습니다.
        _report_progress(
            progress_callback,
            "loading_model",
            35,
            "PaddleOCR 모델을 준비하고 있습니다.",
        )
        ocr_result = self.ocr_service_factory().extract_text(processed_image)
        _report_progress(progress_callback, "extracting", 80, "이미지 OCR이 완료되었습니다.")
        warnings = []
        if not ocr_result.text:
            warnings.append("이미지에서 인식 가능한 텍스트를 찾지 못했습니다.")

        return ExtractedDocument(
            text=ocr_result.text,
            page_count=1,
            document_type="image",
            ocr_image_count=1,
            average_confidence=ocr_result.confidence,
            warnings=warnings,
        )

    @staticmethod
    def _build_response(
        document: ValidatedDocument,
        extracted: ExtractedDocument,
        cleaned_text: str,
        chunks: list[str],
    ) -> OcrDocumentResponse:
        confidence_percent = round(extracted.average_confidence * 100, 1)
        notes = [
            f"문서 유형: {DOCUMENT_TYPE_LABELS.get(extracted.document_type, extracted.document_type)}",
            f"PaddleOCR 처리 이미지: {extracted.ocr_image_count}개",
            *extracted.warnings,
        ]
        if document.file_type in {"docx", "pptx"}:
            notes.insert(0, f"원본 형식: {document.file_type.upper()}")
        review_warning_keywords = (
            "실패",
            "제외",
            "건너뛰",
            "읽지 못",
            "완전하게",
            "다를 수",
            "만 추출",
        )
        needs_review = (
            not cleaned_text
            or confidence_percent < 80
            or any(
                keyword in warning
                for warning in extracted.warnings
                for keyword in review_warning_keywords
            )
        )

        return OcrDocumentResponse(
            documentName=document.file_name,
            pageCount=extracted.page_count,
            characterCount=len(cleaned_text),
            estimatedChunks=len(chunks),
            confidence=confidence_percent,
            extractedText=cleaned_text,
            chunks=chunks,
            readiness="review" if needs_review else "ready",
            notes=notes,
        )


def _build_default_config() -> OcrProcessingConfig:
    return OcrProcessingConfig(
        max_file_bytes=settings.ocr_max_file_size_mb * 1024 * 1024,
        max_pdf_pages=settings.ocr_max_pdf_pages,
        native_text_min_chars=settings.ocr_native_text_min_chars,
        significant_image_area_ratio=settings.ocr_significant_image_area_ratio,
        pdf_render_dpi=settings.ocr_pdf_render_dpi,
        max_image_side=settings.ocr_max_image_side,
        max_image_pixels=settings.ocr_max_image_pixels,
        paddle_device=settings.ocr_paddle_device,
        paddle_language=settings.ocr_paddle_language,
        max_office_uncompressed_bytes=(
            settings.ocr_max_office_uncompressed_size_mb * 1024 * 1024
        ),
        max_office_archive_entries=settings.ocr_max_office_archive_entries,
    )


_default_config = _build_default_config()
_document_processing_service = DocumentProcessingService(
    config=_default_config,
    ocr_service_factory=lambda: get_paddle_ocr_service(
        _default_config.paddle_device,
        _default_config.paddle_language,
    ),
)


async def process_document(
    file: UploadFile,
    chunk_size: int,
    overlap: int,
    progress_callback: ProgressCallback | None = None,
) -> OcrDocumentResponse:
    """Router가 호출하는 기본 Hybrid OCR 중심 함수입니다."""

    return await _document_processing_service.process_document(
        file=file,
        chunk_size=chunk_size,
        overlap=overlap,
        progress_callback=progress_callback,
    )


def _report_progress(
    callback: ProgressCallback | None,
    stage: str,
    progress: int,
    message: str,
) -> None:
    if callback is not None:
        callback(stage, max(0, min(progress, 99)), message)
