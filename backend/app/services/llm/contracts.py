"""LLM Provider가 공유하는 요청, 결과, 오류 계약입니다."""

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class LlmModelDefinition:
    id: str
    label: str
    family: str
    training_stage: str
    description: str
    group: Literal["main", "other"]
    provider_key: str
    provider_model: str
    enabled: bool = True


@dataclass(frozen=True)
class ProviderGenerateRequest:
    prompt: str
    document_name: str | None = None
    system_prompt: str | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class ProviderGenerateResult:
    answer: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None


@dataclass(frozen=True)
class ProviderAvailability:
    available: bool
    message: str | None = None


@dataclass(frozen=True)
class LlmExecutionResult:
    definition: LlmModelDefinition
    provider: str
    is_mock: bool
    result: ProviderGenerateResult
    response_time_seconds: float


@dataclass(frozen=True)
class LlmModelCatalogEntry:
    definition: LlmModelDefinition
    provider: str
    is_mock: bool
    availability: ProviderAvailability


class LlmProvider(Protocol):
    key: str
    is_mock: bool

    async def generate(
        self,
        request: ProviderGenerateRequest,
        model: LlmModelDefinition,
    ) -> ProviderGenerateResult: ...

    async def check_availability(
        self,
        model: LlmModelDefinition,
    ) -> ProviderAvailability: ...


class LlmServiceError(Exception):
    """Frontend에 안전하게 전달할 수 있는 LLM 도메인 오류입니다."""

    status_code = 502


class UnknownLlmModelError(LlmServiceError):
    status_code = 422


class LlmProviderUnavailableError(LlmServiceError):
    status_code = 503


class LlmProviderTimeoutError(LlmServiceError):
    status_code = 504


class LlmProviderAuthenticationError(LlmServiceError):
    status_code = 503


class LlmProviderRateLimitError(LlmServiceError):
    status_code = 429


class LlmContentBlockedError(LlmServiceError):
    status_code = 422


class LlmUpstreamError(LlmServiceError):
    status_code = 502
