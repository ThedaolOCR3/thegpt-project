"""Admin LLM의 단일 실행 및 기존 다중 비교 Backend Mock을 관리합니다."""

import asyncio
import logging
import time
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.schemas.admin import (
    LlmCompareRequest,
    LlmModelResponse,
    LlmRunRequest,
    LlmRunResponse,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LlmMockFixture:
    answer: str
    delay_seconds: float
    output_tokens: int
    should_fail: bool = False


LLM_RUN_FIXTURES = {
    "main-fine-tuned": LlmMockFixture(
        answer=(
            "제공된 근거를 증상, 위험 신호, 권장 행동 순서로 정리하고 문서에서 "
            "확인되지 않는 내용은 추정하지 않습니다. 긴급한 위험 신호가 있다면 "
            "즉시 의료기관의 평가가 필요하다는 점과 이 답변이 전문 진료를 "
            "대신하지 않는다는 한계를 함께 안내합니다."
        ),
        delay_seconds=1.25,
        output_tokens=214,
    ),
    "main-partial": LlmMockFixture(
        answer=(
            "입력된 질문의 핵심 증상을 요약하고 일반적인 주의사항을 안내합니다. "
            "다만 근거 연결과 위험도 구분이 충분하지 않을 수 있으므로 실제 "
            "상담에서는 추가 확인이 필요합니다."
        ),
        delay_seconds=2.05,
        output_tokens=168,
    ),
    "medgemma": LlmMockFixture(
        answer=(
            "제공된 정보만으로 확정적인 진단을 내리기보다 증상의 지속 기간, "
            "복용 약물, 기저질환을 우선 확인해야 합니다. 위험 신호가 있다면 "
            "의료기관 평가를 권고하고 답변의 한계를 명확히 표시합니다."
        ),
        delay_seconds=1.6,
        output_tokens=186,
    ),
    "gemma": LlmMockFixture(
        answer=(
            "문서의 핵심 근거를 증상, 검사 결과, 주의사항 순서로 정리합니다. "
            "이해하기 쉬운 표현을 사용하되 문서에 없는 내용을 추가하지 않고 "
            "필요한 경우 전문가 상담을 안내합니다."
        ),
        delay_seconds=2.35,
        output_tokens=154,
    ),
    "qwen": LlmMockFixture(
        answer=(
            "질문과 관련된 문서 조각을 선별한 뒤 반복되는 근거를 중심으로 답변을 "
            "구성합니다. 서로 충돌하는 내용은 하나로 단정하지 않고 확인이 필요한 "
            "항목으로 구분합니다."
        ),
        delay_seconds=1.85,
        output_tokens=203,
    ),
    "llama": LlmMockFixture(
        answer="",
        delay_seconds=2.65,
        output_tokens=0,
        should_fail=True,
    ),
}

COMPARE_SUPPORTED_MODELS = {"medgemma", "gemma", "qwen"}
COMPARE_MOCK_ANSWERS = {
    "medgemma": "(backend_mock)의료 정보의 한계를 밝히고 위험 신호가 있다면 전문가 평가를 안내합니다.",
    "gemma": "(backend_mock)문서의 핵심 근거를 증상, 검사 결과, 주의사항 순서로 정리합니다.",
    "qwen": "(backend_mock)관련 문서 근거를 선별하고 충돌하는 내용은 확인 항목으로 구분합니다.",
}
COMPARE_RESPONSE_TIMES = (6.42, 9.18, 13.52)
COMPARE_OUTPUT_TOKENS = (186, 154, 203)


async def run_model(request: LlmRunRequest) -> LlmRunResponse:
    """모델 하나의 지연·답변·Token을 Backend에서 생성합니다."""

    fixture = LLM_RUN_FIXTURES.get(request.model_id)
    if fixture is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"지원하지 않는 모델입니다: {request.model_id}",
        )

    started_at = time.perf_counter()
    await asyncio.sleep(fixture.delay_seconds)

    if fixture.should_fail:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mock provider가 일시적으로 응답하지 않았습니다.",
        )

    input_tokens = max(
        64,
        round(len(request.prompt.strip()) * 1.7)
        + (18 if request.document_name else 0),
    )
    reference_note = (
        f" 동일 조건의 참고 문서({request.document_name})가 선택된 Backend Mock 실행입니다."
        if request.document_name
        else " 참고 문서 없이 실행한 Backend Mock 결과입니다."
    )
    response = LlmRunResponse(
        modelId=request.model_id,
        answer=f"{fixture.answer}{reference_note}",
        responseTimeSeconds=time.perf_counter() - started_at,
        inputTokens=input_tokens,
        outputTokens=fixture.output_tokens,
        totalTokens=input_tokens + fixture.output_tokens,
    )
    logger.info(
        "[AdminLLM] Backend mock completed: model=%s, elapsed=%.2fs",
        request.model_id,
        response.response_time_seconds,
    )
    return response


async def compare_models(request: LlmCompareRequest) -> list[LlmModelResponse]:
    """기존 다중 비교 API의 Backend Mock 계약을 유지합니다."""

    validated_request = validate_llm_request(request)
    mock_results = create_mock_model_results(validated_request)
    response = build_compare_response(mock_results)
    logger.info("[AdminLLM] %d mock model responses created", len(response))
    return response


def validate_llm_request(request: LlmCompareRequest) -> LlmCompareRequest:
    """기존 다중 비교 API가 지원하는 모델 목록을 검증합니다."""

    unsupported_models = sorted(
        set(request.model_ids) - COMPARE_SUPPORTED_MODELS,
    )
    if unsupported_models:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"지원하지 않는 모델입니다: {', '.join(unsupported_models)}",
        )
    return request


def create_mock_model_results(
    request: LlmCompareRequest,
) -> list[dict[str, object]]:
    """기존 다중 비교 응답을 Side Effect 없이 생성합니다."""

    input_tokens = max(64, round(len(request.prompt.strip()) * 1.7))
    results: list[dict[str, object]] = []
    for index, model_id in enumerate(request.model_ids):
        results.append(
            {
                "model_id": model_id,
                "status": "success",
                "answer": (
                    f"{request.prompt}의 답변 : "
                    f"{COMPARE_MOCK_ANSWERS[model_id]}"
                ),
                "response_time_seconds": COMPARE_RESPONSE_TIMES[
                    index % len(COMPARE_RESPONSE_TIMES)
                ],
                "input_tokens": input_tokens,
                "output_tokens": COMPARE_OUTPUT_TOKENS[
                    index % len(COMPARE_OUTPUT_TOKENS)
                ],
                "chunk_size": request.chunk_size,
                "overlap": request.overlap,
            }
        )
    return results


def build_compare_response(
    mock_results: list[dict[str, object]],
) -> list[LlmModelResponse]:
    """기존 다중 비교 내부 결과를 Frontend 응답 Schema로 변환합니다."""

    return [LlmModelResponse.model_validate(result) for result in mock_results]
