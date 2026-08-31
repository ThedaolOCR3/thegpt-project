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


async def consult(
    llm_application: Any,
    user_question: str,
    *,
    model_id: str = DEFAULT_MODEL_ID,
    reference_chunks: list[Any] | None = None,
    classifier: BaseQueryClassifier | None = None,
) -> ConsultationResult:
    if risk_detector.detect_emergency(user_question):
        return ConsultationResult(
            answer=risk_detector.EMERGENCY_RESPONSE + DISCLAIMER,
            department=None,
            confidence="낮음",
        )

    classifier = classifier or get_default_classifier()
    department_result: DepartmentResult = classifier.classify(user_question)
    reference_block = build_reference_info_block(reference_chunks)
    messages = build_messages(
        user_question,
        department_result=department_result,
        reference_info_block=reference_block,
    )

    try:
        execution = await llm_application.run(model_id, ProviderGenerateRequest(messages=messages))
        validated = response_validator.validate(execution.result.answer.strip())
        answer = validated + DISCLAIMER
    except Exception:
        # 원격 서버 중지, 모델 미로드, 인증 실패 등이 있어도 채팅은 계속한다.
        logger.exception("consult: LLM 호출 실패 model_id=%s", model_id)
        answer = FALLBACK_ANSWER

    return ConsultationResult(
        answer=answer,
        department=department_result.department,
        confidence=department_result.confidence,
    )
