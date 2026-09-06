import unittest

from pydantic import ValidationError

from ai.ocr import OcrDocumentResult
from app.models.generated import ChunkEmbeddings
from app.schemas.admin import LlmCompareRequest, LlmRunRequest
from app.services.admin_ocr import NEON_VECTOR_DIMENSION
from app.services.embedding_service import (
    EmbeddingUnavailableError,
    EmbeddingValidationError,
    RemoteDualEmbeddingService,
)
from app.services.ocr_workflow import build_admin_ocr_response


class _FakeEmbeddingProvider:
    def __init__(self, name: str, dimension: int) -> None:
        self.name = name
        self.dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimension for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.dimension


def _ocr_result(*, confidence: float, warnings: list[str]) -> OcrDocumentResult:
    return OcrDocumentResult(
        raw_text="원문",
        cleaned_text="정제된 텍스트",
        lines=[],
        page_count=1,
        document_type="image",
        ocr_image_count=1,
        average_confidence=confidence,
        warnings=warnings,
    )


class UnitScopeContractTest(unittest.TestCase):
    def test_admin_response_marks_review_and_sanitizes_file_name(self) -> None:
        response = build_admin_ocr_response(
            file_name=r"C:\upload\..\medical.pdf",
            result=_ocr_result(confidence=0.79, warnings=["일부 이미지를 읽지 못했습니다."]),
            chunks=["정제된 텍스트"],
        )

        self.assertEqual(response.document_name, "medical.pdf")
        self.assertEqual(response.readiness, "review")
        self.assertEqual(response.confidence, 79.0)

    def test_dual_embedding_service_rejects_provider_count_and_dimension(self) -> None:
        with self.subTest("provider count"):
            with self.assertRaises(EmbeddingUnavailableError):
                RemoteDualEmbeddingService([_FakeEmbeddingProvider("only", 1024)])

        with self.subTest("provider dimension"):
            with self.assertRaises(EmbeddingValidationError):
                RemoteDualEmbeddingService(
                    [
                        _FakeEmbeddingProvider("jina", 1024),
                        _FakeEmbeddingProvider("bge", 768),
                    ]
                )

    def test_admin_llm_schema_rejects_invalid_inputs(self) -> None:
        invalid_payloads = (
            (LlmRunRequest, {"prompt": "   ", "modelId": "gemma"}),
            (
                LlmCompareRequest,
                {
                    "prompt": "질문",
                    "modelIds": ["gemma", "gemma"],
                    "chunkSize": 512,
                    "overlap": 50,
                },
            ),
            (
                LlmCompareRequest,
                {
                    "prompt": "질문",
                    "modelIds": ["gemma", "qwen"],
                    "chunkSize": 100,
                    "overlap": 100,
                },
            ),
        )

        for schema, payload in invalid_payloads:
            with self.subTest(schema=schema.__name__, payload=payload):
                with self.assertRaises(ValidationError):
                    schema.model_validate(payload)

    def test_chunk_embeddings_orm_width_matches_storage_contract(self) -> None:
        orm_dimension = ChunkEmbeddings.__table__.c.embedding.type.dim

        self.assertEqual(orm_dimension, NEON_VECTOR_DIMENSION)


if __name__ == "__main__":
    unittest.main()
