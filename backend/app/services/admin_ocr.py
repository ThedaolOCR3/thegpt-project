"""완료된 OCR Job의 Chunk를 Embedding과 함께 Neon에 저장합니다."""

import hashlib
import logging
from typing import Protocol
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.repositories.document_repository import DocumentRepository, SavedDocument
from app.schemas.admin import OcrVectorSaveRequest, OcrVectorSaveResponse
from app.services.embedding_service import (
    EmbeddingService,
    EmbeddingValidationError,
    embedding_service,
)
from app.services.ocr_job_service import OcrJobManager, ocr_job_manager

logger = logging.getLogger(__name__)

NEON_VECTOR_DIMENSION = 1024


class OcrSaveValidationError(Exception):
    """OCR 결과가 저장 가능한 상태가 아닐 때 발생합니다."""


class DocumentSaver(Protocol):
    def save_with_chunks(
        self,
        *,
        original_file_url: str,
        extracted_text: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> SavedDocument: ...


async def save_ocr_result_with_embeddings(
    request: OcrVectorSaveRequest,
    db: Session,
    *,
    job_manager: OcrJobManager = ocr_job_manager,
    embedder: EmbeddingService = embedding_service,
    repository: DocumentSaver | None = None,
) -> OcrVectorSaveResponse:
    """OCR 결과 조회 → Embedding → 문서·Chunk Transaction 저장을 관리합니다."""

    job = job_manager.get_job(request.job_id)
    if job.status != "completed" or job.result is None:
        raise OcrSaveValidationError("완료된 OCR Job만 VectorDB에 저장할 수 있습니다.")
    if not job.result.chunks:
        raise OcrSaveValidationError("저장할 OCR Chunk가 없습니다.")

    logger.info(
        "[OCR SAVE] document save start: job_id=%s chunks=%d",
        request.job_id,
        len(job.result.chunks),
    )
    embeddings = await embedder.embed_chunks(job.result.chunks)
    _validate_embeddings_before_storage(
        chunks=job.result.chunks,
        embeddings=embeddings,
        configured_dimension=embedder.dimension,
    )

    document_repository = repository or DocumentRepository(db)
    saved = document_repository.save_with_chunks(
        original_file_url=_build_job_file_reference(request.job_id, job.result.document_name),
        extracted_text=job.result.extracted_text,
        chunks=job.result.chunks,
        embeddings=embeddings,
    )
    return OcrVectorSaveResponse(
        message=f"OCR 문서와 Chunk {saved.chunk_count}개를 VectorDB에 저장했습니다.",
        documentId=saved.document_id,
        chunkCount=saved.chunk_count,
        embeddingProvider=embedder.provider,
        embeddingDimension=embedder.dimension,
        embeddingModel=embedder.model,
    )


def _build_job_file_reference(job_id: str, document_name: str) -> str:
    """원본 저장소가 생기기 전까지 영구 파일 URL과 구분되는 Job 추적값을 기록합니다."""

    reference = f"ocr-job://{job_id}/{quote(document_name, safe='._-')}"
    if len(reference) <= 500:
        return reference
    name_digest = hashlib.sha256(document_name.encode("utf-8")).hexdigest()
    return f"ocr-job://{job_id}/{name_digest}"


def _validate_embeddings_before_storage(
    *,
    chunks: list[str],
    embeddings: list[list[float]],
    configured_dimension: int,
) -> None:
    """Neon Repository 호출 직전에 실제 Vector가 VECTOR(1024) 계약과 같은지 재검증합니다."""

    if configured_dimension != NEON_VECTOR_DIMENSION:
        raise EmbeddingValidationError(
            "Embedding 설정 차원은 Neon document_chunks.embedding의 "
            f"VECTOR({NEON_VECTOR_DIMENSION})와 같아야 합니다. "
            f"현재 설정: {configured_dimension}"
        )
    if len(chunks) != len(embeddings):
        raise EmbeddingValidationError(
            f"OCR Chunk는 {len(chunks)}개지만 저장할 Embedding은 {len(embeddings)}개입니다."
        )
    for index, vector in enumerate(embeddings):
        if len(vector) != NEON_VECTOR_DIMENSION:
            raise EmbeddingValidationError(
                f"Chunk {index}의 Embedding 차원은 {len(vector)}입니다. "
                f"Neon 저장에는 정확히 {NEON_VECTOR_DIMENSION}차원이 필요합니다."
            )
