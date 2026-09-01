"""Admin OCR·LLM API의 HTTP 요청과 Service를 연결합니다."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.document_repository import DocumentPersistenceError

from app.schemas.admin import (
    LlmCompareRequest,
    LlmModelDefinitionResponse,
    LlmModelResponse,
    LlmRunRequest,
    LlmRunResponse,
    OcrDocumentResponse,
    OcrJobCreatedResponse,
    OcrJobStatusResponse,
    OcrVectorSaveRequest,
    OcrVectorSaveResponse,
    RetrievalEvalResponse,
)
from app.services.admin_evaluation import (
    RetrievalEvalDatasetMissingError,
    RetrievalEvalUnavailableError,
    run_retrieval_evaluation,
)
from app.services.admin_llm import compare_models, list_models, run_model
from app.services.admin_ocr import OcrSaveValidationError, save_ocr_result_with_embeddings
from app.services.embedding_service import (
    EmbeddingGenerationError,
    EmbeddingUnavailableError,
    EmbeddingValidationError,
)
from ai.ocr.errors import (
    DocumentProcessingError,
    DocumentTooLargeError,
    DocumentValidationError,
    OcrUnavailableError,
)
from app.services.ocr_job_service import (
    OcrJobCapacityError,
    OcrJobNotFoundError,
    ocr_job_manager,
)
from app.services.ocr_workflow import process_document
from ai.llm import LlmServiceError

router = APIRouter()


@router.post("/ocr/analyze", response_model=OcrDocumentResponse)
async def analyze_ocr(
    file: Annotated[
        UploadFile,
        File(description="분석할 PDF, PNG, JPG, DOCX, PPTX, JSON, JSONL, CSV, TXT 또는 ZIP 파일"),
    ],
    chunk_size: Annotated[
        int,
        Form(alias="chunkSize", ge=50, le=4096),
    ] = 512,
    overlap: Annotated[int, Form(ge=0)] = 50,
) -> OcrDocumentResponse:
    # Router는 multipart 입력과 HTTP 오류 변환만 담당하고 전체 흐름은 중심 Service에 맡깁니다.
    try:
        return await process_document(
            file=file,
            chunk_size=chunk_size,
            overlap=overlap,
        )
    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except OcrUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/ocr/jobs",
    response_model=OcrJobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_ocr_job(
    file: Annotated[
        UploadFile,
        File(description="분석할 PDF, PNG, JPG, DOCX, PPTX, JSON, JSONL, CSV, TXT 또는 ZIP 파일"),
    ],
    chunk_size: Annotated[
        int,
        Form(alias="chunkSize", ge=50, le=4096),
    ] = 512,
    overlap: Annotated[int, Form(ge=0)] = 50,
) -> OcrJobCreatedResponse:
    # 긴 OCR 처리는 별도 Task에서 실행하고 Frontend에는 조회할 Job ID를 즉시 반환합니다.
    try:
        return await ocr_job_manager.create_job(file, chunk_size, overlap)
    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except OcrJobCapacityError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc


@router.get("/ocr/jobs/{job_id}", response_model=OcrJobStatusResponse)
def get_ocr_job(job_id: str) -> OcrJobStatusResponse:
    try:
        return ocr_job_manager.get_job(job_id)
    except OcrJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/ocr/vector-save", response_model=OcrVectorSaveResponse)
async def save_ocr_vector(
    payload: OcrVectorSaveRequest,
    db: Annotated[Session, Depends(get_db)],
) -> OcrVectorSaveResponse:
    """완료된 OCR Job의 기존 Chunk를 Embedding과 함께 저장합니다."""

    try:
        return await save_ocr_result_with_embeddings(payload, db)
    except OcrJobNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except OcrSaveValidationError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except EmbeddingValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except EmbeddingUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except EmbeddingGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    except DocumentPersistenceError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/llm/compare", response_model=list[LlmModelResponse])
async def compare_llm(payload: LlmCompareRequest) -> list[LlmModelResponse]:
    """기존 다중 비교 계약을 새 Provider 실행 경계로 유지합니다."""

    try:
        return await compare_models(payload)
    except LlmServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/llm/models", response_model=list[LlmModelDefinitionResponse])
async def get_llm_models() -> list[LlmModelDefinitionResponse]:
    """Frontend가 사용할 모델 목록과 현재 Provider 가용성을 반환합니다."""

    return await list_models()


@router.post("/llm/run", response_model=LlmRunResponse)
async def run_llm(payload: LlmRunRequest) -> LlmRunResponse:
    """Model Registry가 선택한 실제 또는 Mock Provider를 실행합니다."""

    try:
        return await run_model(payload)
    except LlmServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/evaluations/retrieval", response_model=RetrievalEvalResponse)
async def get_retrieval_evaluation() -> RetrievalEvalResponse:
    """`scripts/eval_data/*.jsonl` 기준 RAG 검색 정확도(Recall@k, MRR)를 계산합니다.
    호출할 때마다 새로 계산하며(캐시 없음), corpus 규모에 따라 몇십 초 걸릴 수 있습니다."""

    try:
        return await run_retrieval_evaluation()
    except RetrievalEvalDatasetMissingError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except RetrievalEvalUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
