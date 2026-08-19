"""Admin OCR·LLM API의 HTTP 요청과 Service를 연결합니다."""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.admin import (
    LlmCompareRequest,
    LlmModelResponse,
    OcrDocumentResponse,
    OcrJobCreatedResponse,
    OcrJobStatusResponse,
    VectorSaveTestRequest,
    VectorSaveTestResponse,
)
from app.services.admin_llm import compare_models
from app.services.admin_ocr import save_document_test
from app.services.hybrid_ocr.document_processing_service import process_document
from app.services.hybrid_ocr.errors import (
    DocumentProcessingError,
    DocumentTooLargeError,
    DocumentValidationError,
    OcrJobCapacityError,
    OcrJobNotFoundError,
    OcrUnavailableError,
)
from app.services.ocr_job_service import ocr_job_manager

router = APIRouter()


@router.post("/ocr/analyze", response_model=OcrDocumentResponse)
async def analyze_ocr(
    file: Annotated[UploadFile, File(description="분석할 PDF, PNG 또는 JPG 파일")],
    chunk_size: Annotated[
        int,
        Form(alias="chunkSize", ge=100, le=4096),
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
    file: Annotated[UploadFile, File(description="분석할 PDF, PNG 또는 JPG 파일")],
    chunk_size: Annotated[
        int,
        Form(alias="chunkSize", ge=100, le=4096),
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


@router.post("/ocr/vector-save-test", response_model=VectorSaveTestResponse)
async def test_vector_save(payload: VectorSaveTestRequest) -> VectorSaveTestResponse:
    return await save_document_test(payload)


@router.post("/llm/compare", response_model=list[LlmModelResponse])
async def compare_llm(payload: LlmCompareRequest) -> list[LlmModelResponse]:
    # 모델별 Mock 생성 로직을 Router에 노출하지 않고 LLM 중심 함수로 전달합니다.
    return await compare_models(payload)

