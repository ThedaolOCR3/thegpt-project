import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.admin import OcrDocumentResponse


class AdminOcrApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_analyze_keeps_multipart_aliases_and_response_contract(self) -> None:
        admin_result = OcrDocumentResponse(
            documentName="sample.png",
            pageCount=1,
            characterCount=4,
            estimatedChunks=1,
            confidence=95.0,
            extractedText="본문 텍스트",
            chunks=["본문 텍스트"],
            readiness="ready",
            notes=["문서 유형: 이미지"],
        )

        with patch(
            "app.api.admin.router.process_document",
            new=AsyncMock(return_value=admin_result),
        ) as processor:
            response = self.client.post(
                "/api/admin/ocr/analyze",
                files={"file": ("sample.png", b"image", "image/png")},
                data={"chunkSize": "300", "overlap": "40"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["documentName"], "sample.png")
        self.assertEqual(response.json()["extractedText"], "본문 텍스트")
        processor.assert_awaited_once()
        self.assertEqual(processor.await_args.kwargs["chunk_size"], 300)
        self.assertEqual(processor.await_args.kwargs["overlap"], 40)


if __name__ == "__main__":
    unittest.main()
