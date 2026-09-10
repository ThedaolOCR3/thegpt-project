"""RAG/분류 결과를 프롬프트로 조립해 LLM을 호출하고 응답을 검증합니다.

면책 문구는 더 이상 여기서 답변 텍스트에 붙이지 않는다 — 매 답변마다 반복되는 문구라
프론트엔드가 채팅 UI에 별도 경고 배너로 보여준다(MessageBubble.tsx 참고). 이 파일은
검증된 LLM 원문 그대로를 answer로 반환한다.

흐름:
    사용자 질문
        -> 응급 키워드 하드 필터
        -> 진료과 분류
        -> 참고 의료 정보 조립
        -> 프롬프트 조립
        -> 주입받은 LlmApplicationService 호출
        -> 응답 검증(response_validator)

이 모듈은 DB 세션과 Backend 설정을 모른다. Backend는 Admin·일반 API·채팅이
공유하는 Vast.ai 원격 LLM Application을 만들어 consult()에 주입한다.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from ai.llm.contracts import ProviderGenerateRequest

from . import response_validator, risk_detector
from .classifier import BaseQueryClassifier, DepartmentResult, get_default_classifier
from .context import build_reference_info_block
from .prompt_builder import build_messages

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "medgemma"

# Vast.ai 서버(scripts/vastai_medical_llm_server.py)의 GenerateRequest.max_output_tokens
# 기본값은 256이지만 최대 512까지 지원한다. 이 값을 명시적으로 안 넘기면 서버 기본값인
# 256으로 잘려서, 공감+원인 설명+확인 질문+주의사항을 다 담는 답변이 문장 중간에
# 끊기는 게 실제로 관찰됐다(예: "...정확한 진단 후 적절한" 에서 끊김). 서버가 허용하는
# 최댓값(512)을 그대로 요청한다.
DEFAULT_MAX_OUTPUT_TOKENS = 512

FALLBACK_ANSWER = (
    "죄송합니다, 지금은 AI 상담 응답을 생성할 수 없습니다. 잠시 후 다시 시도해주시거나, "
    "증상이 계속되면 의료기관 방문을 고려해주세요."
)


@dataclass(frozen=True)
class ConsultationResult:
    answer: str
    department: str | None
    confidence: str
    # 아래는 전부 관리자 대시보드 로깅용 메타데이터다 — 호출하는 쪽(message.py)이
    # 그대로 consultation_logs에 저장한다. 새로 추가된 필드라 기본값을 둬서 기존
    # 호출부/테스트가 안 깨지게 했다.
    model_id: str | None = None
    provider_key: str | None = None
    is_fallback: bool = False
    is_emergency: bool = False
    rag_hit_count: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    response_time_ms: int | None = None
    error_type: str | None = None
    # provider가 응답을 왜 멈췄는지("stop"=정상 종료, "length"=max_output_tokens에
    # 걸려 잘림 등). 값 자체는 ai/llm/contracts.py의 ProviderGenerateResult가 이미
    # provider별로 정규화해서 채워주고 있었는데, 여기서 안 읽고 버려서 답변이
    # 잘렸는지 여부를 어디서도 추적할 수 없었다(관리자 대시보드에서 "잘림 비율"
    # 같은 지표를 낼 수 없는 gap이었음) - consultation_logs까지 그대로 흘려보낸다.
    finish_reason: str | None = None


async def consult(
    llm_application: Any,
    user_question: str,
    *,
    model_id: str = DEFAULT_MODEL_ID,
    reference_chunks: list[Any] | None = None,
    classifier: BaseQueryClassifier | None = None,
    department_result: DepartmentResult | None = None,
) -> ConsultationResult:
    started_at = time.perf_counter()
    rag_hit_count = len(reference_chunks) if reference_chunks else 0

    # LLM 호출 전 하드 필터 — 프롬프트 지시 준수 여부와 무관하게 작동하는 이중 안전장치.
    if risk_detector.detect_emergency(user_question):
        return ConsultationResult(
            answer=risk_detector.EMERGENCY_RESPONSE,
            department=None,
            confidence="낮음",
            is_emergency=True,
            rag_hit_count=rag_hit_count,
            response_time_ms=round((time.perf_counter() - started_at) * 1000),
        )

    # 호출하는 쪽(message.py)이 RAG 검색의 진료과 부스트에도 같은 분류 결과를
    # 쓰려고 미리 classify()를 해뒀다면 그걸 그대로 받는다 - 키워드 매칭이라
    # 비용은 작지만, 같은 질문을 두 번 분류해서 이론상 다른 결과가 나올 여지를
    # 만들 이유가 없다(분류기가 결정론적이라 실제로는 같은 값이 나오지만).
    if department_result is None:
        classifier = classifier or get_default_classifier()
        department_result = classifier.classify(user_question)
    reference_block = build_reference_info_block(reference_chunks)
    messages = build_messages(
        user_question,
        department_result=department_result,
        reference_info_block=reference_block,
    )

    provider_key: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    is_fallback = False
    error_type: str | None = None
    finish_reason: str | None = None

    try:
        execution = await llm_application.run(
            model_id,
            ProviderGenerateRequest(messages=messages, max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS),
        )
        answer = response_validator.validate(execution.result.answer.strip(), user_question=user_question)
        # 사전 분류(department_result)가 진료과를 못 짚었으면, 이미 나온 최종
        # 답변에서 LLM이 실제로 언급한 진료과로 보완한다 - 사용자 원문보다
        # RAG 참고자료까지 반영한 최종 판단이 더 신뢰도 높은 신호다(response_validator.
        # extract_mentioned_department 참고 - 답변에 진료과가 하나만 명확히
        # 나올 때만 채택하고, 모델이 헷갈려 여러 개를 나열했으면 그대로 None).
        if department_result.department is None:
            mentioned_department = response_validator.extract_mentioned_department(answer)
            if mentioned_department:
                department_result = DepartmentResult(department=mentioned_department, confidence="중간")
        # execution/result는 호출하는 쪽이 넘겨준 llm_application 구현에 달려있어서
        # (테스트에서는 최소 stub을 쓴다), 없는 필드는 조용히 None으로 둔다 —
        # 로깅 메타데이터 때문에 LLM 호출 계약을 더 무겁게 만들지 않기 위함.
        provider_key = getattr(execution, "provider", None)
        input_tokens = getattr(execution.result, "input_tokens", None)
        output_tokens = getattr(execution.result, "output_tokens", None)
        total_tokens = getattr(execution.result, "total_tokens", None)
        finish_reason = getattr(execution.result, "finish_reason", None)
    except Exception as exc:
        # 원격 서버 중지, 모델 미로드, 인증 실패 등 어떤 이유로든 LLM 호출이
        # 실패해도 채팅 자체는 계속 동작해야 한다. 원인은 여기서 로깅하고,
        # 사용자에게는 안전한 대체 응답만 보여준다 — 이건 실제 의료 답변이
        # 아니므로 면책 문구를 붙이지 않는다.
        logger.exception("consult: LLM 호출 실패 model_id=%s", model_id)
        answer = FALLBACK_ANSWER
        is_fallback = True
        error_type = type(exc).__name__

    return ConsultationResult(
        answer=answer,
        department=department_result.department,
        confidence=department_result.confidence,
        model_id=model_id,
        provider_key=provider_key,
        is_fallback=is_fallback,
        rag_hit_count=rag_hit_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        response_time_ms=round((time.perf_counter() - started_at) * 1000),
        error_type=error_type,
        finish_reason=finish_reason,
    )
