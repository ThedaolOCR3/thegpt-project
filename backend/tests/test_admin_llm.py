import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.admin.router import router as admin_router
from app.schemas.admin import LlmRunRequest
from app.services.admin_llm import run_model


class AdminLlmServiceTest(unittest.TestCase):
    def test_single_model_result_is_created_in_backend(self) -> None:
        async def scenario() -> None:
            request = LlmRunRequest(
                prompt="의료 문서의 핵심을 요약해 주세요.",
                modelId="main-fine-tuned",
                documentName="reference.pdf",
            )

            with patch(
                "app.services.admin_llm.asyncio.sleep",
                new=AsyncMock(),
            ) as sleep_mock:
                result = await run_model(request)

            sleep_mock.assert_awaited_once_with(1.25)
            self.assertEqual(result.model_id, "main-fine-tuned")
            self.assertIn("Backend Mock", result.answer)
            self.assertIn("reference.pdf", result.answer)
            self.assertGreater(result.input_tokens, 0)
            self.assertEqual(result.output_tokens, 214)
            self.assertEqual(
                result.total_tokens,
                result.input_tokens + result.output_tokens,
            )

        asyncio.run(scenario())

    def test_unknown_model_is_rejected(self) -> None:
        async def scenario() -> None:
            request = LlmRunRequest(prompt="질문", modelId="unknown-model")

            with self.assertRaises(HTTPException) as raised:
                await run_model(request)

            self.assertEqual(raised.exception.status_code, 422)
            self.assertIn("unknown-model", str(raised.exception.detail))

        asyncio.run(scenario())

    def test_mock_provider_failure_is_reported(self) -> None:
        async def scenario() -> None:
            request = LlmRunRequest(prompt="질문", modelId="llama")

            with patch(
                "app.services.admin_llm.asyncio.sleep",
                new=AsyncMock(),
            ):
                with self.assertRaises(HTTPException) as raised:
                    await run_model(request)

            self.assertEqual(raised.exception.status_code, 503)
            self.assertIn("Mock provider", str(raised.exception.detail))

        asyncio.run(scenario())


class AdminLlmApiTest(unittest.TestCase):
    def test_run_endpoint_uses_camel_case_contract(self) -> None:
        app = FastAPI()
        app.include_router(admin_router, prefix="/api/admin")
        client = TestClient(app)

        with patch(
            "app.services.admin_llm.asyncio.sleep",
            new=AsyncMock(),
        ):
            response = client.post(
                "/api/admin/llm/run",
                json={
                    "prompt": "동일한 질문입니다.",
                    "modelId": "qwen",
                    "documentName": None,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["modelId"], "qwen")
        self.assertIn("Backend Mock", payload["answer"])
        self.assertIn("responseTimeSeconds", payload)
        self.assertEqual(
            payload["totalTokens"],
            payload["inputTokens"] + payload["outputTokens"],
        )


if __name__ == "__main__":
    unittest.main()
