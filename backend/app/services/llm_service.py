from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.llm import (
    LlmCompareResult,
    LlmGenerateResponse,
    LlmMessageInput,
    LlmModelResponse,
)

logger = get_logger("services.llm")


def list_available_models() -> list[LlmModelResponse]:
    from ai.llm import list_models

    return [
        LlmModelResponse(model_id=m.model_id, label=m.label, description=m.description)
        for m in list_models()
    ]


def _get_engine():
    try:
        from ai.llm import get_engine
    except ImportError:
        logger.exception("ai.llm import 실패 — ai/llm/requirements.txt 설치 필요")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "LLM 기능을 사용할 수 없습니다(패키지 미설치)."
        ) from None

    return get_engine(hf_token=settings.hf_token)


def _messages_to_dicts(messages: list[LlmMessageInput]) -> list[dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in messages]


def generate(model_id: str, messages: list[LlmMessageInput]) -> LlmGenerateResponse:
    engine = _get_engine()
    try:
        content = engine.generate(model_id, _messages_to_dicts(messages))
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except RuntimeError as exc:
        # GPU 없음 / 패키지 미설치 등 — engine.py가 이유를 명확한 메시지로 던져준다.
        logger.exception("LLM 생성 실패: model_id=%s", model_id)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except Exception as exc:
        logger.exception("LLM 생성 중 알 수 없는 오류: model_id=%s", model_id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "응답 생성에 실패했습니다.") from exc

    return LlmGenerateResponse(model_id=model_id, content=content)


def compare(model_ids: list[str], messages: list[LlmMessageInput]) -> list[LlmCompareResult]:
    """여러 어댑터에 같은 프롬프트를 넣어 나란히 비교한다 — 관리자 페이지 LLM 탭용.
    하나가 실패해도(예: 어댑터 repo 접근 불가) 나머지는 계속 진행하고, 그 모델의
    결과에만 error를 채워 반환한다."""
    engine = _get_engine()
    message_dicts = _messages_to_dicts(messages)

    results: list[LlmCompareResult] = []
    for model_id in model_ids:
        try:
            content = engine.generate(model_id, message_dicts)
            results.append(LlmCompareResult(model_id=model_id, content=content))
        except Exception as exc:
            logger.exception("LLM 비교 중 %s 실패", model_id)
            results.append(LlmCompareResult(model_id=model_id, error=str(exc)))

    return results
