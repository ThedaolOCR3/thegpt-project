"""완료된 OCR Job의 Chunk를 Embedding과 함께 Neon에 저장합니다."""

import hashlib
import logging
from typing import Protocol
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.repositories.document_repository import DocumentRepository, SavedDocument
from app.schemas.admin import OcrVectorSaveRequest, OcrVectorSaveResponse
from app.services.embedding_service import GeminiEmbeddingService, embedding_service
from app.services.ocr_job_service import OcrJobManager, ocr_job_manager

logger = logging.getLogger(__name__)


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
    embedder: GeminiEmbeddingService = embedding_service,
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
    if len(embeddings) != len(job.result.chunks):
        raise OcrSaveValidationError("OCR Chunk와 Embedding 개수가 일치하지 않습니다.")

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
