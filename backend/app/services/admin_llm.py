"""Admin LLM API와 확장형 LLM Application Service 사이의 Facade입니다."""

import asyncio
import logging

from app.core.config import settings
from app.schemas.admin import (
    LlmCompareRequest,
    LlmModelDefinitionResponse,
    LlmModelResponse,
    LlmRunRequest,
    LlmRunResponse,
)
from app.services.llm.application import LlmApplicationService
from app.services.llm.contracts import LlmExecutionResult, LlmServiceError, ProviderGenerateRequest
from app.services.llm.providers.gemini import GeminiLlmProvider
from app.services.llm.providers.mock import MockLlmProvider
from app.services.llm.providers.ollama import OllamaLlmProvider
from app.services.llm.registry import ProviderRegistry, create_model_registry

logger = logging.getLogger(__name__)


def create_llm_application() -> LlmApplicationService:
    providers = ProviderRegistry(
        (
            OllamaLlmProvider(
                enabled=settings.llm_ollama_enabled,
                base_url=settings.llm_ollama_base_url,
                timeout_seconds=settings.llm_ollama_timeout_seconds,
                max_concurrency=settings.llm_ollama_max_concurrency,
            ),
            GeminiLlmProvider(
                enabled=settings.llm_gemini_enabled,
                api_key=settings.gemini_api_key,
                timeout_seconds=settings.llm_gemini_timeout_seconds,
                max_concurrency=settings.llm_gemini_max_concurrency,
            ),
            MockLlmProvider(),
        )
    )
    return LlmApplicationService(create_model_registry(settings), providers)


llm_application = create_llm_application()


async def list_models() -> list[LlmModelDefinitionResponse]:
    entries = await llm_application.list_models()
    return [
        LlmModelDefinitionResponse(
            id=entry.definition.id,
            label=entry.definition.label,
            family=entry.definition.family,
            trainingStage=entry.definition.training_stage,
            description=entry.definition.description,
            group=entry.definition.group,
            provider=entry.provider,
            providerModel=entry.definition.provider_model,
            enabled=entry.definition.enabled,
            available=entry.availability.available,
            availabilityMessage=entry.availability.message,
            isMock=entry.is_mock,
        )
        for entry in entries
    ]


async def run_model(request: LlmRunRequest) -> LlmRunResponse:
    execution = await llm_application.run(
        request.model_id,
        ProviderGenerateRequest(
            prompt=request.prompt.strip(),
            document_name=request.document_name,
        ),
    )
    logger.info(
        "[AdminLLM] completed: model=%s provider=%s elapsed=%.2fs mock=%s",
        execution.definition.id,
        execution.provider,
        execution.response_time_seconds,
        execution.is_mock,
    )
    return _to_run_response(execution)


def _to_run_response(execution: LlmExecutionResult) -> LlmRunResponse:
    result = execution.result
    return LlmRunResponse(
        modelId=execution.definition.id,
        provider=execution.provider,
        providerModel=execution.definition.provider_model,
        answer=result.answer,
        responseTimeSeconds=execution.response_time_seconds,
        inputTokens=result.input_tokens,
        outputTokens=result.output_tokens,
        totalTokens=result.total_tokens,
        finishReason=result.finish_reason,
        isMock=execution.is_mock,
    )


async def compare_models(request: LlmCompareRequest) -> list[LlmModelResponse]:
    """기존 비교 API를 같은 Provider 실행 경계로 유지합니다."""

    for model_id in request.model_ids:
        llm_application.resolve_model(model_id)
    results = await asyncio.gather(
        *(
            llm_application.run(
                model_id,
                ProviderGenerateRequest(
                    prompt=request.prompt.strip(),
                    document_name=request.document_name,
                ),
            )
            for model_id in request.model_ids
        ),
        return_exceptions=True,
    )
    response: list[LlmModelResponse] = []
    for model_id, result in zip(request.model_ids, results, strict=True):
        if isinstance(result, LlmServiceError):
            response.append(
                LlmModelResponse(
                    modelId=model_id,
                    status="error",
                    error=str(result),
                    responseTimeSeconds=0,
                    inputTokens=None,
                    outputTokens=None,
                    chunkSize=request.chunk_size,
                    overlap=request.overlap,
                )
            )
            continue
        if isinstance(result, BaseException):
            raise result
        response.append(
            LlmModelResponse(
                modelId=model_id,
                status="success",
                answer=result.result.answer,
                responseTimeSeconds=result.response_time_seconds,
                inputTokens=result.result.input_tokens,
                outputTokens=result.result.output_tokens,
                chunkSize=request.chunk_size,
                overlap=request.overlap,
            )
        )
    return response
