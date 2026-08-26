"""공통 Model/Provider Registry와 MedGemma Adapter 정의입니다."""

from collections.abc import Iterable
from dataclasses import dataclass

from ai.llm.contracts import (
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


MEDGEMMA_MODEL_DEFINITIONS: tuple[LlmModelDefinition, ...] = (
    LlmModelDefinition(
        id="medgemma-screening",
        provider_key="medgemma",
        provider_model="gon-0130/medgemma-4b-lora-consultation-v2",
        label="MedGemma (스크리닝)",
        family="MedGemma LoRA",
        training_stage="초기 학습 버전",
        description="무료 Colab에서 학습한 초기 버전 — KorMedMCQA + GenMedGPT-5k-ko 2종.",
        group="other",
    ),
    LlmModelDefinition(
        id="medgemma-main",
        provider_key="medgemma",
        provider_model="gon-0130/medgemma-4b-lora-consultation-main-v2",
        label="MedGemma (메인)",
        family="MedGemma LoRA",
        training_stage="메인 학습 버전",
        description="유료 Colab에서 학습한 메인 버전 — 지식/추론보강/대화형 11개 데이터셋.",
        group="other",
    ),
)


@dataclass(frozen=True)
class ModelEntry:
    """기존 `/api/llm/models`와 Engine 호출을 위한 호환 Projection입니다."""

    model_id: str
    adapter_repo: str
    label: str
    description: str


MODEL_REGISTRY: list[ModelEntry] = [
    ModelEntry(
        model_id=definition.id,
        adapter_repo=definition.provider_model,
        label=definition.label,
        description=definition.description,
    )
    for definition in MEDGEMMA_MODEL_DEFINITIONS
]

DEFAULT_MODEL_ID = MODEL_REGISTRY[0].model_id


def get_model_entry(model_id: str) -> ModelEntry:
    for entry in MODEL_REGISTRY:
        if entry.model_id == model_id:
            return entry
    raise KeyError(f"등록되지 않은 model_id입니다: {model_id}")


def list_models() -> list[ModelEntry]:
    return list(MODEL_REGISTRY)
