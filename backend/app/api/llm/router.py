from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth.dependencies import get_current_user, require_admin
from app.models.generated import Users
from app.schemas.llm import (
    LlmCompareRequest,
    LlmCompareResult,
    LlmGenerateRequest,
    LlmGenerateResponse,
    LlmModelResponse,
)
from app.services.llm_service import compare, generate, list_available_models

router = APIRouter()


@router.get("/models", response_model=list[LlmModelResponse])
def get_models() -> list[LlmModelResponse]:
    """등록된 MedGemma 어댑터 목록 — 채팅 모델 선택 드롭다운, 관리자 비교 화면이 공유해서 쓴다.
    레지스트리만 읽는 가벼운 조회라 GPU/모델 로드 없이 항상 응답 가능하다."""
    return list_available_models()


@router.post("/generate", response_model=LlmGenerateResponse)
def generate_response(
    payload: LlmGenerateRequest,
    current_user: Annotated[Users, Depends(get_current_user)],
) -> LlmGenerateResponse:
    """단일 모델로 응답 생성 — GPU가 있는 환경에서만 동작(없으면 503)."""
    return generate(payload.model_id, payload.messages)


@router.post("/compare", response_model=list[LlmCompareResult])
def compare_models(
    payload: LlmCompareRequest,
    current_user: Annotated[Users, Depends(require_admin)],
) -> list[LlmCompareResult]:
    """여러 모델에 같은 프롬프트를 넣어 비교 — 관리자 페이지 LLM 탭용, 관리자 전용."""
    return compare(payload.model_ids, payload.messages)
