"""Google GenAI SDK를 사용하는 Gemini Provider입니다."""

import asyncio
import importlib.util
import logging
from collections.abc import Callable
from typing import Any

from app.services.llm.contracts import (
    LlmContentBlockedError,
    LlmModelDefinition,
    LlmProviderAuthenticationError,
    LlmProviderRateLimitError,
    LlmProviderTimeoutError,
    LlmProviderUnavailableError,
    LlmUpstreamError,
    ProviderAvailability,
    ProviderGenerateRequest,
    ProviderGenerateResult,
)

logger = logging.getLogger(__name__)


def _create_google_client(api_key: str) -> Any:
    from google import genai
    return genai.Client(api_key=api_key)


class GeminiLlmProvider:
    key = "gemini"
    is_mock = False

    def __init__(
        self,
        *,
        enabled: bool,
        api_key: str | None,
        timeout_seconds: float,
        max_concurrency: int,
        client_factory: Callable[[str], Any] = _create_google_client,
    ) -> None:
        self._enabled = enabled
        self._api_key = api_key.strip() if api_key else None
        self._timeout_seconds = max(1.0, timeout_seconds)
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self._client_factory = client_factory

    async def check_availability(self, model: LlmModelDefinition) -> ProviderAvailability:
        del model
        if not self._enabled:
            return ProviderAvailability(False, "Gemini Provider가 비활성화되었습니다.")
        if not self._api_key:
            return ProviderAvailability(False, "최상위 .env에 GEMINI_API_KEY를 설정하세요.")
        try:
            installed = importlib.util.find_spec("google.genai") is not None
        except ModuleNotFoundError:
            installed = False
        if not installed:
            return ProviderAvailability(False, "google-genai 패키지가 설치되지 않았습니다.")
        return ProviderAvailability(True)

    async def generate(self, request: ProviderGenerateRequest, model: LlmModelDefinition) -> ProviderGenerateResult:
        if not self._enabled:
            raise LlmProviderUnavailableError("Gemini Provider가 비활성화되었습니다.")
        if not self._api_key:
            raise LlmProviderUnavailableError("최상위 .env에 GEMINI_API_KEY를 설정하세요.")
        client: Any = None
        async_client: Any = None
        try:
            client = self._client_factory(self._api_key)
            async_client = client.aio
            async with self._semaphore:
                response = await asyncio.wait_for(
                    async_client.models.generate_content(model=model.provider_model, contents=request.prompt),
                    timeout=self._timeout_seconds,
                )
        except TimeoutError as exc:
            raise LlmProviderTimeoutError("Gemini 응답 제한시간을 초과했습니다.") from exc
        except Exception as exc:
            self._raise_safe_provider_error(exc, model.provider_model)
        finally:
            await self._close_clients(async_client, client)
        answer = self._response_text(response)
        if not answer:
            if self._is_blocked_response(response):
                raise LlmContentBlockedError("Gemini 안전 정책에 따라 요청을 처리하지 못했습니다.")
            raise LlmUpstreamError("Gemini가 빈 답변을 반환했습니다.")
        usage = getattr(response, "usage_metadata", None)
        input_tokens = self._optional_int(getattr(usage, "prompt_token_count", None))
        output_tokens = self._optional_int(getattr(usage, "candidates_token_count", None))
        total_tokens = self._optional_int(getattr(usage, "total_token_count", None))
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        return ProviderGenerateResult(
            answer=answer,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            finish_reason=self._finish_reason(response),
        )

    @staticmethod
    async def _close_clients(async_client: Any, client: Any) -> None:
        if async_client is not None and callable(getattr(async_client, "aclose", None)):
            try:
                await async_client.aclose()
            except Exception:
                pass
        if client is not None and callable(getattr(client, "close", None)):
            try:
                client.close()
            except Exception:
                pass

    @staticmethod
    def _response_text(response: Any) -> str:
        try:
            text = response.text
        except Exception:
            return ""
        return text.strip() if isinstance(text, str) else ""

    @staticmethod
    def _is_blocked_response(response: Any) -> bool:
        feedback = getattr(response, "prompt_feedback", None)
        reason = getattr(feedback, "block_reason", None)
        if reason is not None and str(reason).upper() not in {"0", "BLOCK_REASON_UNSPECIFIED", "NONE"}:
            return True
        return any(
            "SAFETY" in str(getattr(candidate, "finish_reason", "")).upper()
            for candidate in (getattr(response, "candidates", None) or [])
        )

    @staticmethod
    def _finish_reason(response: Any) -> str | None:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None
        reason = getattr(candidates[0], "finish_reason", None)
        value = getattr(reason, "value", reason)
        return str(value) if value is not None else None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    @staticmethod
    def _status_code(error: Exception) -> int | None:
        for candidate in (
            getattr(error, "code", None),
            getattr(error, "status_code", None),
            getattr(getattr(error, "response", None), "status_code", None),
        ):
            if isinstance(candidate, int):
                return candidate
        return None

    @classmethod
    def _raise_safe_provider_error(cls, error: Exception, provider_model: str) -> None:
        status_code = cls._status_code(error)
        provider_status = getattr(error, "status", None)
        logger.warning(
            "Gemini request failed: model=%s error_type=%s status_code=%s provider_status=%s",
            provider_model,
            type(error).__name__,
            status_code,
            provider_status,
        )
        if status_code == 429:
            raise LlmProviderRateLimitError(
                "Gemini 무료 할당량을 초과했습니다. Google AI Studio에서 현재 할당량을 확인하세요."
            ) from error
        if status_code in {401, 403}:
            raise LlmProviderAuthenticationError(
                "Gemini API 인증에 실패했습니다. GEMINI_API_KEY 설정을 확인하세요."
            ) from error
        if status_code == 404:
            raise LlmProviderUnavailableError(
                f"Gemini 모델을 찾을 수 없습니다: {provider_model}. "
                "LLM_GEMINI_MODEL 설정을 확인하세요."
            ) from error
        if status_code == 400 and "safety" in str(error).lower():
            raise LlmContentBlockedError("Gemini 안전 정책에 따라 요청을 처리하지 못했습니다.") from error
        if status_code is not None and status_code >= 500:
            raise LlmUpstreamError("Gemini 서비스에서 오류가 발생했습니다.") from error
        raise LlmUpstreamError("Gemini 요청을 처리하지 못했습니다.") from error
