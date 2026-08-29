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
from ai.llm.providers.remote_http import RemoteHttpLlmProvider

logger = logging.getLogger(__name__)


def create_admin_model_registry() -> ModelRegistry:
    """Backend Settings를 기존 Admin 모델 정의로 변환합니다."""

    return ModelRegistry(
        (
            LlmModelDefinition(
                id="gemma",
                label="Gemma Medical",
                family="Gemma 2 2B",
                training_stage="한국어 의료 QLoRA",
                description="Vast.ai V100에서 실행하는 Gemma 2 2B 한국어 의료 QLoRA 모델입니다.",
                group="main",
                provider_key="remote-http",
                provider_model=settings.llm_remote_gemma_model,
            ),
            LlmModelDefinition(
                id="medgemma",
                label="MedGemma (최종)",
                family="MedGemma LoRA",
                training_stage="의료 상담 최종 LoRA",
                description="Vast.ai V100에서 MedGemma 4B base에 최종 상담 LoRA를 적용한 모델입니다.",
                group="main",
                provider_key="remote-http",
                provider_model=settings.llm_remote_medgemma_final_model,
            ),
            LlmModelDefinition(
                id="medgemma-dataset",
                label="MedGemma (데이터셋)",
                family="MedGemma LoRA",
                training_stage="의료 상담 데이터셋 LoRA",
                description="최종 모델과 같은 MedGemma 4B base에 데이터셋 LoRA를 적용한 비교 모델입니다.",
                group="main",
                provider_key="remote-http",
                provider_model=settings.llm_remote_medgemma_dataset_model,
            ),
            LlmModelDefinition(
                id="qwen",
                label="Qwen Medical",
                family="Qwen3 4B",
                training_stage="QLoRA 의료 파인튜닝",
                description="Vast.ai V100에서 실행하는 Qwen3 4B 의료 QLoRA 모델입니다.",
                group="other",
                provider_key="remote-http",
                provider_model=settings.llm_remote_qwen_model,
            ),
            LlmModelDefinition(
                id="llama",
                label="Llama Medical",
                family="Llama 3.2 3B",
                training_stage="QLoRA 의료 파인튜닝",
                description="Vast.ai V100에서 실행하는 Llama 3.2 3B 의료 QLoRA 모델입니다.",
                group="other",
                provider_key="remote-http",
                provider_model=settings.llm_remote_llama_model,
            ),
        )
    )


def create_llm_application() -> LlmApplicationService:
    providers = ProviderRegistry(
        (
            RemoteHttpLlmProvider(
                enabled=settings.llm_remote_enabled,
                base_url=settings.llm_remote_base_url,
                api_key=settings.llm_remote_api_key,
                timeout_seconds=settings.llm_remote_timeout_seconds,
                max_concurrency=settings.llm_remote_max_concurrency,
            ),
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
