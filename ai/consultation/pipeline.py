"""RAG/분류 결과를 프롬프트로 조립해 LLM을 호출하고 면책 문구를 붙입니다.

흐름:
    사용자 질문
        -> 응급 키워드 하드 필터
        -> 진료과 분류
        -> 참고 의료 정보 조립
        -> 프롬프트 조립
        -> 주입받은 LlmApplicationService 호출
        -> 응답 검증과 면책 문구 후처리

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

DISCLAIMER = (
    "\n\n※ 본 답변은 참고용 정보이며 의학적 진단을 대체하지 않습니다. "
    "정확한 진단은 반드시 의료진과 상담하세요."
)

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


async def consult(
    llm_application: Any,
    user_question: str,
    *,
    model_id: str = DEFAULT_MODEL_ID,
    reference_chunks: list[Any] | None = None,
    classifier: BaseQueryClassifier | None = None,
) -> ConsultationResult:
    started_at = time.perf_counter()
    rag_hit_count = len(reference_chunks) if reference_chunks else 0

    # LLM 호출 전 하드 필터 — 프롬프트 지시 준수 여부와 무관하게 작동하는 이중 안전장치.
    if risk_detector.detect_emergency(user_question):
        return ConsultationResult(
            answer=risk_detector.EMERGENCY_RESPONSE + DISCLAIMER,
            department=None,
            confidence="낮음",
            is_emergency=True,
            rag_hit_count=rag_hit_count,
            response_time_ms=round((time.perf_counter() - started_at) * 1000),
        )

    classifier = classifier or get_default_classifier()
    department_result: DepartmentResult = classifier.classify(user_question)
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

    try:
        execution = await llm_application.run(model_id, ProviderGenerateRequest(messages=messages))
        validated = response_validator.validate(execution.result.answer.strip())
        answer = validated + DISCLAIMER
        # execution/result는 호출하는 쪽이 넘겨준 llm_application 구현에 달려있어서
        # (테스트에서는 최소 stub을 쓴다), 없는 필드는 조용히 None으로 둔다 —
        # 로깅 메타데이터 때문에 LLM 호출 계약을 더 무겁게 만들지 않기 위함.
        provider_key = getattr(execution, "provider", None)
        input_tokens = getattr(execution.result, "input_tokens", None)
        output_tokens = getattr(execution.result, "output_tokens", None)
        total_tokens = getattr(execution.result, "total_tokens", None)
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
    )
