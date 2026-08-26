import json
import unittest
from unittest.mock import AsyncMock, patch

from ai.llm import (
    LlmApplicationService,
    LlmModelDefinition,
    LlmProviderUnavailableError,
    ProviderAvailability,
    ProviderGenerateResult,
    ProviderRegistry,
)
from app.services import admin_llm


class FakeProvider:
    def __init__(self, key: str, *, is_mock: bool, should_fail: bool = False) -> None:
        self.key = key
        self.is_mock = is_mock
        self.should_fail = should_fail
        self.generate = AsyncMock(side_effect=self._generate)

    async def _generate(self, request, model):
        del request
        if self.should_fail:
            raise LlmProviderUnavailableError("테스트 Provider 실패")
        return ProviderGenerateResult(
            answer=f"{model.id} answer",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            finish_reason="stop",
        )

    async def check_availability(self, model: LlmModelDefinition) -> ProviderAvailability:
        del model
        return ProviderAvailability(not self.should_fail)


class AdminLlmApiTest(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.api.admin.router import router as admin_router

        self.providers = (
            FakeProvider("ollama", is_mock=False),
            FakeProvider("gemini", is_mock=False),
            FakeProvider("mock", is_mock=True),
        )
        self.application = LlmApplicationService(
            admin_llm.create_admin_model_registry(),
            ProviderRegistry(self.providers),
        )
        app = FastAPI()
        app.include_router(admin_router, prefix="/api/admin")
        self.client = TestClient(app)

    def test_model_catalog_and_run_keep_camel_case_contract(self) -> None:
        with patch.object(admin_llm, "llm_application", self.application):
            catalog_response = self.client.get("/api/admin/llm/models")
            run_response = self.client.post(
                "/api/admin/llm/run",
                json={"prompt": "질문", "modelId": "ollama-gemma3", "documentName": None},
            )

        self.assertEqual(catalog_response.status_code, 200)
        catalog = catalog_response.json()
        self.assertEqual(len(catalog), 6)
        self.assertEqual(catalog[0]["id"], "ollama-gemma3")
        self.assertFalse(catalog[0]["isMock"])
        self.assertTrue(catalog[2]["isMock"])
        self.assertNotIn("apiKey", json.dumps(catalog))

        self.assertEqual(run_response.status_code, 200)
        payload = run_response.json()
        self.assertEqual(payload["provider"], "ollama")
        self.assertEqual(payload["providerModel"], "gemma3:1b")
        self.assertFalse(payload["isMock"])
        self.assertEqual(payload["totalTokens"], 30)

        request = self.providers[0].generate.await_args.args[0]  # type: ignore[union-attr]
        self.assertEqual(request.messages[0].role, "user")
        self.assertEqual(request.messages[0].content, "질문")

    def test_unknown_model_returns_422(self) -> None:
        with patch.object(admin_llm, "llm_application", self.application):
            response = self.client.post(
                "/api/admin/llm/run",
                json={"prompt": "질문", "modelId": "main-fine-tuned"},
            )

        self.assertEqual(response.status_code, 422)

    def test_compare_isolates_one_provider_failure(self) -> None:
        providers = ProviderRegistry(
            (
                FakeProvider("ollama", is_mock=False),
                FakeProvider("gemini", is_mock=False),
                FakeProvider("mock", is_mock=True, should_fail=True),
            )
        )
        application = LlmApplicationService(
            admin_llm.create_admin_model_registry(),
            providers,
        )

        with patch.object(admin_llm, "llm_application", application):
            response = self.client.post(
                "/api/admin/llm/compare",
                json={
                    "prompt": "질문",
                    "modelIds": ["ollama-gemma3", "medgemma"],
                    "chunkSize": 512,
                    "overlap": 50,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload[0]["status"], "success")
        self.assertEqual(payload[1]["status"], "error")
        self.assertNotIn("Traceback", payload[1]["error"])


if __name__ == "__main__":
    unittest.main()
