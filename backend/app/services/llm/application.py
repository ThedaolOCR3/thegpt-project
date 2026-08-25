"""Model Registry와 Provider 실행을 조율하는 LLM Application Service입니다."""

import asyncio
import time

from app.services.llm.contracts import (
    LlmExecutionResult,
    LlmModelCatalogEntry,
    LlmModelDefinition,
    LlmProviderUnavailableError,
    ProviderAvailability,
    ProviderGenerateRequest,
)
from app.services.llm.registry import ModelRegistry, ProviderRegistry


class LlmApplicationService:
    def __init__(
        self,
        model_registry: ModelRegistry,
        provider_registry: ProviderRegistry,
    ) -> None:
        self.model_registry = model_registry
        self.provider_registry = provider_registry

    def resolve_model(self, model_id: str) -> LlmModelDefinition:
        return self.model_registry.resolve(model_id)

    async def list_models(self) -> list[LlmModelCatalogEntry]:
        definitions = self.model_registry.list()
        availability = await asyncio.gather(
            *(self._check_availability(definition) for definition in definitions)
        )
        return [
            LlmModelCatalogEntry(
                definition=definition,
                provider=definition.provider_key,
                is_mock=self.provider_registry.resolve(
                    definition.provider_key
                ).is_mock,
                availability=model_availability,
            )
            for definition, model_availability in zip(
                definitions, availability, strict=True
            )
        ]

    async def _check_availability(
        self,
        definition: LlmModelDefinition,
    ) -> ProviderAvailability:
        if not definition.enabled:
            return ProviderAvailability(False, "비활성화된 모델입니다.")
        try:
            provider = self.provider_registry.resolve(definition.provider_key)
            return await provider.check_availability(definition)
        except LlmProviderUnavailableError as exc:
            return ProviderAvailability(False, str(exc))

    async def run(
        self,
        model_id: str,
        request: ProviderGenerateRequest,
    ) -> LlmExecutionResult:
        definition = self.model_registry.resolve(model_id)
        if not definition.enabled:
            raise LlmProviderUnavailableError("비활성화된 모델입니다.")

        provider = self.provider_registry.resolve(definition.provider_key)
        started_at = time.perf_counter()
        result = await provider.generate(request, definition)
        return LlmExecutionResult(
            definition=definition,
            provider=provider.key,
            is_mock=provider.is_mock,
            result=result,
            response_time_seconds=time.perf_counter() - started_at,
        )
