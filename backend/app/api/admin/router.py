"""Admin OCR·LLM Mock API의 HTTP 요청과 Service를 연결합니다."""

from fastapi import APIRouter

from app.schemas.admin import (
    LlmCompareRequest,
    LlmModelResponse,
    OcrAnalyzeRequest,
    OcrDocumentResponse,
    VectorSaveTestRequest,
    VectorSaveTestResponse,
)
from app.services.admin_llm import compare_models
from app.services.admin_ocr import analyze_document, save_document_test

router = APIRouter()


@router.post("/ocr/analyze", response_model=OcrDocumentResponse)
async def analyze_ocr(payload: OcrAnalyzeRequest) -> OcrDocumentResponse:
    # Router는 HTTP 연결만 담당하고 전체 실행 순서는 OCR 중심 함수에 위임합니다.
    return await analyze_document(payload)


@router.post("/ocr/vector-save-test", response_model=VectorSaveTestResponse)
async def test_vector_save(payload: VectorSaveTestRequest) -> VectorSaveTestResponse:
    return await save_document_test(payload)


@router.post("/llm/compare", response_model=list[LlmModelResponse])
async def compare_llm(payload: LlmCompareRequest) -> list[LlmModelResponse]:
    # 모델별 Mock 생성 로직을 Router에 노출하지 않고 LLM 중심 함수로 전달합니다.
    return await compare_models(payload)

