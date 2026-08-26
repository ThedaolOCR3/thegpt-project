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
from ai.llm import (
    LlmApplicationService,
    LlmExecutionResult,
    LlmModelDefinition,
    LlmServiceError,
    ModelRegistry,
    ProviderGenerateRequest,
    ProviderRegistry,
)
from ai.llm.providers.gemini import GeminiLlmProvider
from ai.llm.providers.mock import MockLlmProvider
from ai.llm.providers.ollama import OllamaLlmProvider

logger = logging.getLogger(__name__)


def create_admin_model_registry() -> ModelRegistry:
    """Backend Settings를 기존 Admin 모델 정의로 변환합니다."""

    return ModelRegistry(
        (
            LlmModelDefinition(
                id="ollama-gemma3",
                label="Gemma 3 (Local)",
                family="Local LLM",
                training_stage="순정 로컬 모델",
                description="로컬 Ollama에서 실행하는 순정 Gemma 3 모델입니다.",
                group="main",
                provider_key="ollama",
                provider_model=settings.llm_ollama_model,
            ),
            LlmModelDefinition(
                id="gemini",
                label="Gemini 3.5 Flash-Lite",
                family="Google Gemini API",
                training_stage="외부 API 모델",
                description="Backend에서 Gemini API를 호출하는 실제 모델입니다.",
                group="main",
                provider_key="gemini",
                provider_model=settings.llm_gemini_model,
            ),
            LlmModelDefinition(
                id="medgemma",
                label="MedGemma",
                family="외부 비교 모델",
                training_stage="Mock 비교군",
                description="의료 응답 형식을 검증하는 Mock 모델입니다.",
                group="other",
                provider_key="mock",
                provider_model="medgemma",
            ),
            LlmModelDefinition(
                id="gemma",
                label="Gemma (Mock)",
                family="외부 비교 모델",
                training_stage="Mock 비교군",
                description="실제 로컬 Gemma 3와 구분되는 Mock 비교 모델입니다.",
                group="other",
                provider_key="mock",
                provider_model="gemma",
            ),
            LlmModelDefinition(
                id="qwen",
                label="Qwen",
                family="외부 비교 모델",
                training_stage="Mock 비교군",
                description="Qwen 응답 형태를 가정한 Mock 비교 모델입니다.",
                group="other",
                provider_key="mock",
                provider_model="qwen",
            ),
            LlmModelDefinition(
                id="llama",
                label="Llama",
                family="외부 비교 모델",
                training_stage="Mock 오류 비교군",
                description="모델별 오류 격리 UI를 확인하는 Mock 모델입니다.",
                group="other",
                provider_key="mock",
                provider_model="llama",
            ),
        )
    )


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
    return LlmApplicationService(create_admin_model_registry(), providers)


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
        ProviderGenerateRequest.from_prompt(
            request.prompt.strip(),
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
                ProviderGenerateRequest.from_prompt(
                    request.prompt.strip(),
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
