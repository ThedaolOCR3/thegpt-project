import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from ai.llm import (
    LlmMessage,
    LlmProviderRateLimitError,
    LlmProviderUnavailableError,
    ProviderGenerateRequest,
)
from ai.llm.providers.gemini import GeminiLlmProvider
from tests.ai.llm.helpers import model_definition, prompt_request


def gemini_definition():
    return model_definition(
        model_id="gemini",
        provider_key="gemini",
        provider_model="gemini-3.5-flash-lite",
    )


def fake_client(*, response=None, error=None):
    generate_content = AsyncMock(return_value=response, side_effect=error)
    async_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content),
        aclose=AsyncMock(),
    )
    client = SimpleNamespace(aio=async_client, close=Mock())
    return client, async_client


class GeminiProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_async_sdk_response_and_usage_are_mapped(self) -> None:
        response = SimpleNamespace(
            text="Gemini 실제 응답",
            usage_metadata=SimpleNamespace(
                prompt_token_count=7,
                candidates_token_count=11,
                total_token_count=18,
            ),
            candidates=[SimpleNamespace(finish_reason="STOP")],
            prompt_feedback=None,
        )
        client, async_client = fake_client(response=response)
        provider = GeminiLlmProvider(
            enabled=True,
            api_key="test-key",
            timeout_seconds=10,
            max_concurrency=1,
            client_factory=lambda api_key: client,
        )

        result = await provider.generate(prompt_request(), gemini_definition())

        async_client.models.generate_content.assert_awaited_once_with(
            model="gemini-3.5-flash-lite",
            contents="질문",
        )
        self.assertEqual(result.answer, "Gemini 실제 응답")
        self.assertEqual((result.input_tokens, result.output_tokens, result.total_tokens), (7, 11, 18))
        async_client.aclose.assert_awaited_once()
        client.close.assert_called_once()

    async def test_conversation_roles_and_system_instruction_are_preserved(self) -> None:
        response = SimpleNamespace(
            text="답변",
            usage_metadata=None,
            candidates=[],
            prompt_feedback=None,
        )
        client, async_client = fake_client(response=response)
        provider = GeminiLlmProvider(
            enabled=True,
            api_key="test-key",
            timeout_seconds=10,
            max_concurrency=1,
            client_factory=lambda api_key: client,
        )
        request = ProviderGenerateRequest(
            messages=(
                LlmMessage(role="system", content="근거만 답변"),
                LlmMessage(role="user", content="질문 1"),
                LlmMessage(role="assistant", content="답변 1"),
                LlmMessage(role="user", content="질문 2"),
            ),
            max_output_tokens=200,
        )

        await provider.generate(request, gemini_definition())

        kwargs = async_client.models.generate_content.await_args.kwargs
        self.assertEqual(
            [item["role"] for item in kwargs["contents"]],
            ["user", "model", "user"],
        )
        self.assertEqual(kwargs["config"]["system_instruction"], "근거만 답변")
        self.assertEqual(kwargs["config"]["max_output_tokens"], 200)

    async def test_quota_error_is_safe_and_mapped(self) -> None:
        error = RuntimeError("secret provider details")
        error.code = 429  # type: ignore[attr-defined]
        client, _ = fake_client(error=error)
        provider = GeminiLlmProvider(
            enabled=True,
            api_key="must-not-leak",
            timeout_seconds=10,
            max_concurrency=1,
            client_factory=lambda api_key: client,
        )

        with self.assertRaises(LlmProviderRateLimitError) as raised:
            await provider.generate(prompt_request(), gemini_definition())

        self.assertNotIn("must-not-leak", str(raised.exception))

    async def test_missing_model_is_mapped_with_configured_model_name(self) -> None:
        error = RuntimeError("provider details")
        error.code = 404  # type: ignore[attr-defined]
        client, _ = fake_client(error=error)
        provider = GeminiLlmProvider(
            enabled=True,
            api_key="must-not-leak",
            timeout_seconds=10,
            max_concurrency=1,
            client_factory=lambda api_key: client,
        )

        with self.assertRaises(LlmProviderUnavailableError) as raised:
            await provider.generate(prompt_request(), gemini_definition())

        self.assertIn("gemini-3.5-flash-lite", str(raised.exception))
        self.assertNotIn("must-not-leak", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
