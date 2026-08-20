"""Model ID와 실제 LLM Provider를 연결하는 Registry입니다."""

from collections.abc import Iterable

from app.core.config import Settings
from app.services.llm.contracts import (
    LlmModelDefinition,
    LlmProvider,
    LlmProviderUnavailableError,
    UnknownLlmModelError,
)


class ModelRegistry:
    def __init__(self, definitions: Iterable[LlmModelDefinition]) -> None:
        self._definitions = {definition.id: definition for definition in definitions}

    def list(self) -> tuple[LlmModelDefinition, ...]:
        return tuple(self._definitions.values())

    def resolve(self, model_id: str) -> LlmModelDefinition:
        definition = self._definitions.get(model_id)
        if definition is None:
            raise UnknownLlmModelError(f"지원하지 않는 모델입니다: {model_id}")
        return definition


class ProviderRegistry:
    def __init__(self, providers: Iterable[LlmProvider]) -> None:
        self._providers = {provider.key: provider for provider in providers}

    def resolve(self, provider_key: str) -> LlmProvider:
        provider = self._providers.get(provider_key)
        if provider is None:
            raise LlmProviderUnavailableError(
                f"LLM Provider가 등록되지 않았습니다: {provider_key}"
            )
        return provider


def create_model_registry(settings: Settings) -> ModelRegistry:
    """표시 순서를 포함한 Admin LLM 모델 목록의 단일 기준을 만듭니다."""

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
