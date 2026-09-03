"""완료된 OCR Job의 Chunk를 Embedding과 함께 Neon에 저장합니다."""

import hashlib
import logging
from collections.abc import Iterator
from typing import Protocol
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.document_repository import DocumentRepository, SavedDocument
from app.schemas.admin import OcrVectorSaveRequest, OcrVectorSaveResponse
from app.services.embedding_service import (
    EmbeddingBatch,
    EmbeddingService,
    EmbeddingValidationError,
    embedding_service,
)
from app.services.ocr_job_service import OcrJobManager, ocr_job_manager
from app.services.large_document_service import iter_chunk_artifact
from app.services.r2_storage import R2StorageService, rag_r2_storage

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
        embeddings_by_provider: dict[str, list[list[float]]],
        chunk_metadata: dict | None = None,
    ) -> SavedDocument: ...


def _build_chunk_metadata(result) -> dict | None:
    """관리자 업로드 청크가 RAG 검색 소프트 부스트(source_tier)/출처 표시(source)를
    받을 수 있게 자동으로 채운다 - 관리자가 따로 입력할 UI 없이, OCR Job이 이미
    알고 있는 정보(웹 URL로 수집했는지, 파일 업로드인지)만으로 정한다.

    source_tier는 ai/rag/ingestion 어댑터들이 쓰는 척도를 그대로 따른다(1=공식기관
    원문, 2=전문가 검수, 3=AI 생성/미검수, 4=번역+미검수) - 웹 URL 수집은 관리자가
    출처를 직접 골라서 넣은 것이라 2로 둔다(파일 업로드가 어디서 왔는지는 알 수
    없어 tier를 안 매기고 중립(무boost/무penalty)으로 둔다 - rag_search_service.
    _boost_multiplier가 없는 tier는 1.0으로 처리하므로 안전하다)."""
    source_type = getattr(result, "source_type", None)
    source_url = getattr(result, "source_url", None)
    if source_type == "url" and source_url:
        return {"source": source_url, "source_tier": 2}
    return None


async def save_ocr_result_with_embeddings(
    request: OcrVectorSaveRequest,
    db: Session,
    *,
    job_manager: OcrJobManager = ocr_job_manager,
    embedder: EmbeddingService = embedding_service,
    repository: DocumentSaver | None = None,
    storage: R2StorageService = rag_r2_storage,
) -> OcrVectorSaveResponse:
    """OCR 결과 조회 → Embedding → 문서·Chunk Transaction 저장을 관리합니다."""

    job = job_manager.get_job(request.job_id)
    if job.status != "completed" or job.result is None:
        raise OcrSaveValidationError("완료된 OCR Job만 VectorDB에 저장할 수 있습니다.")
    if not job.result.chunks:
        raise OcrSaveValidationError("저장할 OCR Chunk가 없습니다.")

    document_repository = repository or DocumentRepository(db)
    chunk_metadata = _build_chunk_metadata(job.result)
    if job.result.chunk_artifact_key:
        return await _save_staged_result(
            result=job.result,
            embedder=embedder,
            repository=document_repository,
            storage=storage,
            chunk_metadata=chunk_metadata,
        )

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

    saved = document_repository.save_with_chunks(
        original_file_url=(
            job.result.source_url
            if job.result.source_type == "url" and job.result.source_url
            else _build_job_file_reference(request.job_id, job.result.document_name)
        ),
        extracted_text=job.result.extracted_text,
        chunks=job.result.chunks,
        embeddings_by_provider=embeddings.vectors_by_provider,
        chunk_metadata=chunk_metadata,
    )
    return OcrVectorSaveResponse(
        message=f"OCR 문서와 Chunk {saved.chunk_count}개를 VectorDB에 저장했습니다.",
        documentId=saved.document_id,
        chunkCount=saved.chunk_count,
        embeddingProvider=embedder.provider,
        embeddingDimension=embedder.dimension,
        embeddingModel=embedder.model,
    )


async def _save_staged_result(
    *,
    result,
    embedder: EmbeddingService,
    repository,
    storage: R2StorageService,
    chunk_metadata: dict | None = None,
) -> OcrVectorSaveResponse:
    artifact_key = result.chunk_artifact_key
    if not artifact_key or not result.original_object_key:
        raise OcrSaveValidationError("대용량 OCR 저장 정보가 올바르지 않습니다.")

    document_id = repository.begin_staged_save(
        original_file_url=_build_r2_file_reference(result.original_object_key),
        extracted_text=result.extracted_text,
    )
    chunk_count = 0
    try:
        for chunks in _batched(
            iter_chunk_artifact(artifact_key, storage),
            settings.embedding_batch_size,
        ):
            embeddings = await embedder.embed_chunks(chunks)
            _validate_embeddings_before_storage(
                chunks=chunks,
                embeddings=embeddings,
                configured_dimension=embedder.dimension,
            )
            repository.append_staged_chunks(
                document_id=document_id,
                start_index=chunk_count,
                chunks=chunks,
                embeddings_by_provider=embeddings.vectors_by_provider,
                chunk_metadata=chunk_metadata,
            )
            chunk_count += len(chunks)
        if chunk_count == 0:
            raise OcrSaveValidationError("저장할 OCR Chunk가 없습니다.")
        saved = repository.finish_staged_save(document_id, chunk_count)
    except Exception:
        try:
            repository.abort_staged_save(document_id)
        except Exception:
            logger.exception("실패한 대용량 OCR 문서 정리 실패: document_id=%s", document_id)
        raise

    try:
        storage.delete_object(artifact_key)
    except Exception:
        logger.exception("저장 완료 후 Chunk artifact 정리 실패: key=%s", artifact_key)

    return OcrVectorSaveResponse(
        message=f"OCR 문서와 Chunk {saved.chunk_count}개를 VectorDB에 저장했습니다.",
        documentId=saved.document_id,
        chunkCount=saved.chunk_count,
        embeddingProvider=embedder.provider,
        embeddingDimension=embedder.dimension,
        embeddingModel=embedder.model,
    )


def _batched(values: Iterator[str], batch_size: int) -> Iterator[list[str]]:
    batch: list[str] = []
    for value in values:
        batch.append(value)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _build_r2_file_reference(object_key: str) -> str:
    reference = f"r2:///{object_key}"
    if len(reference) <= 500:
        return reference
    return f"r2:///admin-rag-uploads/{hashlib.sha256(object_key.encode()).hexdigest()}"


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
    embeddings: EmbeddingBatch,
    configured_dimension: int,
) -> None:
    """Neon 저장 직전에 Jina/BGE 실제 Vector가 1024차원 계약과 같은지 재검증합니다."""

    if configured_dimension != NEON_VECTOR_DIMENSION:
        raise EmbeddingValidationError(
            "Embedding 설정 차원은 Jina/BGE 실제 Vector 계약인 "
            f"VECTOR({NEON_VECTOR_DIMENSION})와 같아야 합니다. "
            f"현재 설정: {configured_dimension}"
        )
    if len(embeddings.vectors_by_provider) != 2:
        raise EmbeddingValidationError("Jina/BGE 두 Provider의 Embedding이 모두 필요합니다.")
    for provider_name, vectors in embeddings.vectors_by_provider.items():
        if len(chunks) != len(vectors):
            raise EmbeddingValidationError(
                f"OCR Chunk는 {len(chunks)}개지만 {provider_name} Vector는 {len(vectors)}개입니다."
            )
        for index, vector in enumerate(vectors):
            if len(vector) != NEON_VECTOR_DIMENSION:
                raise EmbeddingValidationError(
                    f"{provider_name} Chunk {index}의 Embedding 차원은 {len(vector)}입니다. "
                    f"Neon 저장에는 정확히 {NEON_VECTOR_DIMENSION}차원이 필요합니다."
                )
