import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from app.services import admin_llm
from app.services.llm.application import LlmApplicationService
from app.services.llm.contracts import (
    LlmModelDefinition,
    ProviderAvailability,
    ProviderGenerateRequest,
    ProviderGenerateResult,
    UnknownLlmModelError,
)
from app.services.llm.providers.ollama import OllamaLlmProvider
from app.services.llm.registry import ModelRegistry, ProviderRegistry, create_model_registry


def model_definition(
    *,
    model_id: str = "ollama-gemma3",
    provider_key: str = "ollama",
    provider_model: str = "gemma3:1b",
    group: str = "main",
) -> LlmModelDefinition:
    return LlmModelDefinition(
        id=model_id,
        label=model_id,
        family="test",
        training_stage="test",
        description="test",
        group=group,  # type: ignore[arg-type]
        provider_key=provider_key,
        provider_model=provider_model,
    )


class FakeProvider:
    def __init__(self, key: str, *, is_mock: bool) -> None:
        self.key = key
        self.is_mock = is_mock
        self.generate = AsyncMock(
            return_value=ProviderGenerateResult(
                answer=f"{key} answer",
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                finish_reason="stop",
            )
        )

    async def check_availability(self, model: LlmModelDefinition) -> ProviderAvailability:
        del model
        return ProviderAvailability(True)


class RegistryAndApplicationTest(unittest.IsolatedAsyncioTestCase):
    def test_final_registry_contains_one_real_and_four_mock_models(self) -> None:
        settings = SimpleNamespace(
            llm_ollama_model="gemma3:1b",
        )
        definitions = create_model_registry(settings).list()  # type: ignore[arg-type]
        mapping = {definition.id: definition.provider_key for definition in definitions}

        self.assertEqual(
            list(mapping),
            ["ollama-gemma3", "medgemma", "gemma", "qwen", "llama"],
        )
        self.assertEqual(mapping["ollama-gemma3"], "ollama")
        self.assertTrue(all(mapping[item] == "mock" for item in ("medgemma", "gemma", "qwen", "llama")))
        self.assertNotIn("main-fine-tuned", mapping)
        self.assertNotIn("main-partial", mapping)

    async def test_provider_key_switches_mock_to_real_without_application_change(self) -> None:
        mock_provider = FakeProvider("mock", is_mock=True)
        ollama_provider = FakeProvider("ollama", is_mock=False)
        providers = ProviderRegistry((mock_provider, ollama_provider))
        request = ProviderGenerateRequest(prompt="질문")

        mock_app = LlmApplicationService(
            ModelRegistry((model_definition(model_id="medgemma", provider_key="mock"),)),
            providers,
        )
        real_app = LlmApplicationService(
            ModelRegistry((model_definition(model_id="medgemma", provider_key="ollama"),)),
            providers,
        )

        mock_result = await mock_app.run("medgemma", request)
        real_result = await real_app.run("medgemma", request)

        self.assertTrue(mock_result.is_mock)
        self.assertFalse(real_result.is_mock)
        self.assertEqual(real_result.provider, "ollama")

    def test_unknown_model_is_rejected(self) -> None:
        registry = ModelRegistry(())
        with self.assertRaises(UnknownLlmModelError):
            registry.resolve("unknown")


class OllamaProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_chat_response_and_real_token_counts_are_mapped(self) -> None:
        captured: dict[str, object] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/tags":
                return httpx.Response(200, json={"models": [{"name": "gemma3:1b"}]})
            captured.update(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "message": {"role": "assistant", "content": "실제 응답"},
                    "prompt_eval_count": 12,
                    "eval_count": 34,
                    "done_reason": "stop",
                },
            )

        provider = OllamaLlmProvider(
            enabled=True,
            base_url="http://127.0.0.1:11434",
            timeout_seconds=10,
            max_concurrency=1,
            transport=httpx.MockTransport(handler),
        )
        definition = model_definition()

        availability = await provider.check_availability(definition)
        result = await provider.generate(ProviderGenerateRequest(prompt="질문"), definition)

        self.assertTrue(availability.available)
        self.assertEqual(captured["model"], "gemma3:1b")
        self.assertFalse(captured["stream"])
        self.assertEqual(result.answer, "실제 응답")
        self.assertEqual((result.input_tokens, result.output_tokens, result.total_tokens), (12, 34, 46))

    async def test_missing_model_is_unavailable(self) -> None:
        provider = OllamaLlmProvider(
            enabled=True,
            base_url="http://127.0.0.1:11434",
            timeout_seconds=10,
            max_concurrency=1,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"models": []})
            ),
        )
        availability = await provider.check_availability(model_definition())
        self.assertFalse(availability.available)
        self.assertIn("설치되지", availability.message or "")


class AdminLlmApiTest(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.api.admin.router import router as admin_router

        settings = SimpleNamespace(
            llm_ollama_model="gemma3:1b",
        )
        self.providers = (
            FakeProvider("ollama", is_mock=False),
            FakeProvider("mock", is_mock=True),
        )
        self.application = LlmApplicationService(
            create_model_registry(settings),  # type: ignore[arg-type]
            ProviderRegistry(self.providers),
        )
        app = FastAPI()
        app.include_router(admin_router, prefix="/api/admin")
        self.client = TestClient(app)

    def test_model_catalog_and_run_use_camel_case_contract(self) -> None:
        with patch.object(admin_llm, "llm_application", self.application):
            catalog_response = self.client.get("/api/admin/llm/models")
            run_response = self.client.post(
                "/api/admin/llm/run",
                json={"prompt": "질문", "modelId": "ollama-gemma3", "documentName": None},
            )

        self.assertEqual(catalog_response.status_code, 200)
        catalog = catalog_response.json()
        self.assertEqual(len(catalog), 5)
        self.assertEqual(catalog[0]["id"], "ollama-gemma3")
        self.assertFalse(catalog[0]["isMock"])
        self.assertTrue(catalog[1]["isMock"])
        self.assertNotIn("apiKey", json.dumps(catalog))

        self.assertEqual(run_response.status_code, 200)
        payload = run_response.json()
        self.assertEqual(payload["provider"], "ollama")
        self.assertEqual(payload["providerModel"], "gemma3:1b")
        self.assertFalse(payload["isMock"])
        self.assertEqual(payload["totalTokens"], 30)

    def test_removed_and_unknown_models_return_422(self) -> None:
        with patch.object(admin_llm, "llm_application", self.application):
            response = self.client.post(
                "/api/admin/llm/run",
                json={"prompt": "질문", "modelId": "main-fine-tuned"},
            )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
