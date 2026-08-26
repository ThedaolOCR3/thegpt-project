import asyncio

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.llm import (
    LlmCompareResult,
    LlmGenerateResponse,
    LlmMessageInput,
    LlmModelResponse,
)
from ai.llm import (
    LlmApplicationService,
    LlmMessage,
    LlmProviderUnavailableError,
    LlmServiceError,
    MEDGEMMA_MODEL_DEFINITIONS,
    ModelRegistry,
    ProviderGenerateRequest,
    ProviderRegistry,
    UnknownLlmModelError,
)
from ai.llm.providers.medgemma import MedGemmaLlmProvider

logger = get_logger("services.llm")


def list_available_models() -> list[LlmModelResponse]:
    return [
        LlmModelResponse(
            model_id=definition.id,
            label=definition.label,
            description=definition.description,
        )
        for definition in MEDGEMMA_MODEL_DEFINITIONS
    ]


def create_llm_application() -> LlmApplicationService:
    provider = MedGemmaLlmProvider(
        enabled=settings.llm_medgemma_enabled,
        hf_token=settings.hf_token,
        max_concurrency=settings.llm_medgemma_max_concurrency,
    )
    return LlmApplicationService(
        ModelRegistry(MEDGEMMA_MODEL_DEFINITIONS),
        ProviderRegistry((provider,)),
    )


llm_application = create_llm_application()


def _to_core_request(messages: list[LlmMessageInput]) -> ProviderGenerateRequest:
    return ProviderGenerateRequest(
        messages=tuple(
            LlmMessage(role=message.role, content=message.content)
            for message in messages
        )
    )


async def generate(model_id: str, messages: list[LlmMessageInput]) -> LlmGenerateResponse:
    try:
        execution = await llm_application.run(model_id, _to_core_request(messages))
    except UnknownLlmModelError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except LlmProviderUnavailableError as exc:
        logger.exception("LLM 생성 실패: model_id=%s", model_id)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except LlmServiceError as exc:
        logger.exception("LLM 생성 실패: model_id=%s", model_id)
        raise HTTPException(exc.status_code, str(exc)) from exc

    return LlmGenerateResponse(model_id=model_id, content=execution.result.answer)


async def compare(model_ids: list[str], messages: list[LlmMessageInput]) -> list[LlmCompareResult]:
    """여러 어댑터에 같은 프롬프트를 넣어 나란히 비교한다 — 관리자 페이지 LLM 탭용.
    하나가 실패해도(예: 어댑터 repo 접근 불가) 나머지는 계속 진행하고, 그 모델의
    결과에만 error를 채워 반환한다."""
    request = _to_core_request(messages)
    executions = await asyncio.gather(
        *(llm_application.run(model_id, request) for model_id in model_ids),
        return_exceptions=True,
    )
    results: list[LlmCompareResult] = []
    for model_id, execution in zip(model_ids, executions, strict=True):
        if isinstance(execution, BaseException):
            logger.warning(
                "LLM 비교 중 모델 실행 실패: model_id=%s error_type=%s",
                model_id,
                type(execution).__name__,
            )
            error = str(execution) if isinstance(execution, LlmServiceError) else "응답 생성에 실패했습니다."
            results.append(LlmCompareResult(model_id=model_id, error=error))
            continue
        results.append(
            LlmCompareResult(model_id=model_id, content=execution.result.answer)
        )

    return results
