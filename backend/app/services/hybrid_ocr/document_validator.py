"""업로드 문서를 실제 OCR 처리 전에 검증합니다."""

from io import BytesIO
from pathlib import Path

import pymupdf
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.services.hybrid_ocr.errors import (
    DocumentTooLargeError,
    DocumentValidationError,
)
from app.services.hybrid_ocr.models import OcrProcessingConfig, ValidatedDocument

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SUPPORTED_PDF_MIME_TYPES = {"application/pdf", "application/octet-stream"}
SUPPORTED_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "application/octet-stream",
}


async def validate_document(
    file: UploadFile,
    config: OcrProcessingConfig,
) -> ValidatedDocument:
    """파일명, 크기, MIME, 실제 바이너리 형식을 순서대로 검증합니다."""

    raw_file_name = (file.filename or "").replace("\\", "/")
    file_name = Path(raw_file_name).name
    extension = Path(file_name).suffix.lower()
    content_type = (
        (file.content_type or "application/octet-stream")
        .split(";", 1)[0]
        .strip()
        .lower()
    )

    if not file_name or extension not in SUPPORTED_IMAGE_EXTENSIONS | {".pdf"}:
        raise DocumentValidationError("PDF, PNG, JPG 파일만 업로드할 수 있습니다.")

    # 선언된 크기만 신뢰하지 않고 제한보다 한 바이트 더 읽어 실제 크기를 확인합니다.
    content = await file.read(config.max_file_bytes + 1)
    if not content:
        raise DocumentValidationError("빈 파일은 분석할 수 없습니다.")
    if len(content) > config.max_file_bytes:
        max_size_mb = config.max_file_bytes // (1024 * 1024)
        raise DocumentTooLargeError(
            f"파일 크기는 {max_size_mb}MB 이하여야 합니다."
        )

    if extension == ".pdf":
        _validate_pdf(content, content_type, config.max_pdf_pages)
        file_type = "pdf"
    else:
        _validate_image(
            content,
            extension,
            content_type,
            config.max_image_pixels,
        )
        file_type = "image"

    return ValidatedDocument(
        file_name=file_name,
        content_type=content_type,
        file_type=file_type,
        content=content,
    )


def validate_chunk_options(chunk_size: int, overlap: int) -> None:
    """Chunk가 앞으로 진행하지 못하는 잘못된 Overlap 설정을 차단합니다."""

    if overlap >= chunk_size:
        raise DocumentValidationError("Overlap은 Chunk Size보다 작아야 합니다.")


def _validate_pdf(content: bytes, content_type: str, max_pages: int) -> None:
    if content_type not in SUPPORTED_PDF_MIME_TYPES:
        raise DocumentValidationError("PDF 파일의 MIME Type이 올바르지 않습니다.")
    if b"%PDF-" not in content[:1024]:
        raise DocumentValidationError("PDF signature를 확인할 수 없습니다.")

    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.needs_pass or document.is_encrypted:
                raise DocumentValidationError("암호화된 PDF는 분석할 수 없습니다.")
            if document.page_count == 0:
                raise DocumentValidationError("페이지가 없는 PDF는 분석할 수 없습니다.")
            if document.page_count > max_pages:
                raise DocumentValidationError(
                    f"PDF는 최대 {max_pages}페이지까지 분석할 수 있습니다."
                )
            # 모든 페이지를 한 번 열어 손상된 페이지 객체가 있는지도 미리 확인합니다.
            for page_number in range(document.page_count):
                document.load_page(page_number)
    except DocumentValidationError:
        raise
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise DocumentValidationError("손상되었거나 읽을 수 없는 PDF입니다.") from exc


def _validate_image(
    content: bytes,
    extension: str,
    content_type: str,
    max_pixels: int,
) -> None:
    if content_type not in SUPPORTED_IMAGE_MIME_TYPES:
        raise DocumentValidationError("이미지 파일의 MIME Type이 올바르지 않습니다.")

    expected_formats = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}
    try:
        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > max_pixels:
                raise DocumentValidationError(
                    "이미지 해상도가 허용 범위를 초과했습니다."
                )
            image.load()
            if image.format != expected_formats[extension]:
                raise DocumentValidationError(
                    "확장자와 실제 이미지 형식이 일치하지 않습니다."
                )
    except DocumentValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise DocumentValidationError("손상되었거나 읽을 수 없는 이미지입니다.") from exc
