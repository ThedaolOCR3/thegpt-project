"""Admin LLM 비교 요청의 검증, Mock 생성, 응답 조립 순서를 관리합니다."""

import logging

from fastapi import HTTPException, status

from app.schemas.admin import LlmCompareRequest, LlmModelResponse

logger = logging.getLogger(__name__)
SUPPORTED_MODELS = {"medgemma", "gemma", "qwen", "llama"}
MOCK_ANSWERS = {
    "medgemma": "(backend_mock)의료 정보의 한계를 밝히고 위험 신호가 있다면 전문가 평가를 안내합니다.",
    "gemma": "(backend_mock)문서의 핵심 근거를 증상, 검사 결과, 주의사항 순서로 정리합니다.",
    "qwen": "(backend_mock)관련 문서 근거를 선별하고 충돌하는 내용은 확인 항목으로 구분합니다.",
    "llama": "(backend_mock)질문의 의도를 요약하고 문서 근거와 다음 확인 사항을 제시합니다.",
}
RESPONSE_TIMES = (6.42, 9.18, 13.52)
OUTPUT_TOKENS = (186, 154, 203)


async def compare_models(request: LlmCompareRequest) -> list[LlmModelResponse]:
    """Request → 검증 → 모델별 Mock → Response의 전체 실행 순서를 관리합니다."""

    validated_request = validate_llm_request(request)

    # 실제 모델이 준비되면 아래 Mock 생성 호출만 Ollama/LLM 호출로 교체합니다.
    mock_results = create_mock_model_results(validated_request)

    response = build_compare_response(mock_results)
    logger.info("[AdminLLM] %d mock model responses created", len(response))
    return response


def validate_llm_request(request: LlmCompareRequest) -> LlmCompareRequest:
    """지원 모델을 한 번에 확인하고 잘못된 모델 목록을 명확히 반환합니다."""

    unsupported_models = sorted(set(request.model_ids) - SUPPORTED_MODELS)
    if unsupported_models:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"지원하지 않는 모델입니다: {', '.join(unsupported_models)}",
        )
    return request


def create_mock_model_results(request: LlmCompareRequest) -> list[dict[str, object]]:
    """향후 실제 다중 LLM 호출로 교체할 단일 Mock 처리 지점입니다."""

    input_tokens = max(64, round(len(request.prompt.strip()) * 1.7))
    results: list[dict[str, object]] = []
    for index, model_id in enumerate(request.model_ids):
        if model_id == "llama":
            results.append({
                "model_id": model_id, "status": "error",
                "error": "[backend_mock]provider가 일시적으로 응답하지 않았습니다.",
                "response_time_seconds": 8.74, "input_tokens": 0, "output_tokens": 0,
                "chunk_size": request.chunk_size, "overlap": request.overlap,
            })
            continue
        results.append({
            "model_id": model_id, "status": "success", "answer": MOCK_ANSWERS[model_id],
            "response_time_seconds": RESPONSE_TIMES[index % len(RESPONSE_TIMES)],
            "input_tokens": input_tokens,
            "output_tokens": OUTPUT_TOKENS[index % len(OUTPUT_TOKENS)],
            "chunk_size": request.chunk_size, "overlap": request.overlap,
        })
    return results


def build_compare_response(mock_results: list[dict[str, object]]) -> list[LlmModelResponse]:
    """모델별 내부 결과를 고정된 Frontend 응답 Schema로 변환합니다."""

    return [LlmModelResponse.model_validate(result) for result in mock_results]
