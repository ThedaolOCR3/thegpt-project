import asyncio
import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.document_repository import (
    DocumentPersistenceError,
    DocumentRepository,
    SavedDocument,
)
from app.schemas.admin import OcrDocumentResponse, OcrVectorSaveRequest
from app.services.admin_ocr import (
    OcrSaveValidationError,
    _build_job_file_reference,
    save_ocr_result_with_embeddings,
)
from app.services.embedding_service import (
    EmbeddingGenerationError,
    EmbeddingUnavailableError,
    EmbeddingValidationError,
    GeminiEmbeddingService,
    create_embedding_service,
)


class GeminiEmbeddingServiceTest(unittest.TestCase):
    def test_configured_provider_factory_selects_gemini(self) -> None:
        service = create_embedding_service(
            _embedding_settings(embedding_provider="gemini")
        )

        self.assertIsInstance(service, GeminiEmbeddingService)
        self.assertEqual(service.provider, "gemini")
        self.assertEqual(service.model, "gemini-embedding-001")
        self.assertEqual(service.dimension, 1024)

    def test_unknown_provider_is_rejected_clearly(self) -> None:
        with self.assertRaises(EmbeddingUnavailableError) as raised:
            # 실제 BGE-M3 Provider가 등록되기 전에는 설정만 바꿔 우연히 실행되지 않아야 합니다.
            create_embedding_service(_embedding_settings(embedding_provider="bge-m3"))
        self.assertIn("bge-m3", str(raised.exception))
        self.assertIn("gemini", str(raised.exception))

    def test_batch_embedding_keeps_count_order_and_dimension(self) -> None:
        async def scenario() -> None:
            response = SimpleNamespace(
                embeddings=[
                    SimpleNamespace(values=[0.1] * 1024),
                    SimpleNamespace(values=[0.2] * 1024),
                ]
            )
            embed_content = AsyncMock(return_value=response)
            async_client = SimpleNamespace(
                models=SimpleNamespace(embed_content=embed_content),
                aclose=AsyncMock(),
            )
            client = SimpleNamespace(aio=async_client, close=Mock())
            service = _embedding_service(lambda _api_key: client)

            vectors = await service.embed_chunks(["첫 Chunk", "둘째 Chunk"])

            self.assertEqual(len(vectors), 2)
            self.assertEqual(len(vectors[0]), 1024)
            self.assertEqual((vectors[0][0], vectors[1][0]), (0.1, 0.2))
            embed_content.assert_awaited_once_with(
                model="gemini-embedding-001",
                contents=["첫 Chunk", "둘째 Chunk"],
                config={
                    "task_type": "RETRIEVAL_DOCUMENT",
                    "output_dimensionality": 1024,
                },
            )
            async_client.aclose.assert_awaited_once()
            client.close.assert_called_once()

        asyncio.run(scenario())

    def test_empty_chunk_is_rejected_before_provider_call(self) -> None:
        service = _embedding_service(Mock())
        with self.assertRaises(EmbeddingValidationError):
            asyncio.run(service.embed_chunks(["정상", "  "]))

    def test_wrong_vector_count_is_rejected(self) -> None:
        async def scenario() -> None:
            response = SimpleNamespace(
                embeddings=[SimpleNamespace(values=[0.1] * 1024)]
            )
            service = _embedding_service(_client_factory(response))
            with self.assertRaises(EmbeddingValidationError):
                await service.embed_chunks(["첫 Chunk", "둘째 Chunk"])

        asyncio.run(scenario())

    def test_wrong_vector_dimension_is_rejected(self) -> None:
        async def scenario() -> None:
            response = SimpleNamespace(
                embeddings=[SimpleNamespace(values=[0.1] * 128)]
            )
            service = _embedding_service(_client_factory(response))
            with self.assertRaises(EmbeddingValidationError):
                await service.embed_chunks(["Chunk"])

        asyncio.run(scenario())

    def test_provider_failure_is_mapped_without_leaking_details(self) -> None:
        async def scenario() -> None:
            embed_content = AsyncMock(side_effect=RuntimeError("secret upstream detail"))
            client = SimpleNamespace(
                aio=SimpleNamespace(
                    models=SimpleNamespace(embed_content=embed_content),
                    aclose=AsyncMock(),
                ),
                close=Mock(),
            )
            service = _embedding_service(lambda _api_key: client)
            with self.assertRaises(EmbeddingGenerationError) as raised:
                await service.embed_chunks(["Chunk"])
            self.assertNotIn("secret", str(raised.exception))

        asyncio.run(scenario())


class DocumentRepositoryTest(unittest.TestCase):
    def test_document_and_all_chunks_are_committed_together(self) -> None:
        document_id = uuid4()
        db = FakeSession(document_id=document_id)
        repository = DocumentRepository(db)  # type: ignore[arg-type]

        saved = repository.save_with_chunks(
            original_file_url="ocr-job://job/sample.pdf",
            extracted_text="전체 텍스트",
            chunks=["첫 Chunk", "둘째 Chunk"],
            embeddings=[[0.1] * 1024, [0.2] * 1024],
        )

        self.assertEqual(saved, SavedDocument(document_id=document_id, chunk_count=2))
        self.assertTrue(db.committed)
        self.assertFalse(db.rolled_back)
        self.assertEqual([row.chunk_index for row in db.chunk_rows], [0, 1])
        self.assertTrue(all(row.document_id == document_id for row in db.chunk_rows))
        self.assertEqual([row.chunk_text for row in db.chunk_rows], ["첫 Chunk", "둘째 Chunk"])
        self.assertTrue(all(len(row.embedding) == 1024 for row in db.chunk_rows))

    def test_db_failure_rolls_back_whole_save(self) -> None:
        db = FakeSession(document_id=uuid4(), fail_commit=True)
        repository = DocumentRepository(db)  # type: ignore[arg-type]

        with self.assertRaises(DocumentPersistenceError):
            repository.save_with_chunks(
                original_file_url="ocr-job://job/sample.pdf",
                extracted_text="전체 텍스트",
                chunks=["Chunk"],
                embeddings=[[0.1] * 1024],
            )

        self.assertFalse(db.committed)
        self.assertTrue(db.rolled_back)


class OcrVectorSaveFlowTest(unittest.TestCase):
    def test_completed_job_uses_existing_chunks_and_returns_saved_result(self) -> None:
        async def scenario() -> None:
            job_manager = Mock()
            job_manager.get_job.return_value = SimpleNamespace(
                status="completed",
                result=_ocr_result(),
            )
            embedder = FakeEmbedder()
            repository = FakeRepository()
            document_id = uuid4()
            repository.result = SavedDocument(document_id=document_id, chunk_count=2)

            response = await save_ocr_result_with_embeddings(
                OcrVectorSaveRequest(jobId="completed-job"),
                Mock(spec=Session),
                job_manager=job_manager,
                embedder=embedder,  # type: ignore[arg-type]
                repository=repository,
            )

            self.assertEqual(embedder.received_chunks, ["첫 Chunk", "둘째 Chunk"])
            self.assertEqual(repository.saved["chunks"], ["첫 Chunk", "둘째 Chunk"])
            self.assertEqual(response.document_id, document_id)
            self.assertEqual(response.chunk_count, 2)
            self.assertEqual(response.embedding_provider, "fake")
            self.assertEqual(response.embedding_dimension, 1024)

        asyncio.run(scenario())

    def test_non_1024_provider_is_rejected_before_repository(self) -> None:
        async def scenario() -> None:
            job_manager = Mock()
            job_manager.get_job.return_value = SimpleNamespace(
                status="completed",
                result=_ocr_result(),
            )
            repository = FakeRepository()
            embedder = FakeEmbedder(dimension=768)

            with self.assertRaises(EmbeddingValidationError) as raised:
                await save_ocr_result_with_embeddings(
                    OcrVectorSaveRequest(jobId="completed-job"),
                    Mock(spec=Session),
                    job_manager=job_manager,
                    embedder=embedder,  # type: ignore[arg-type]
                    repository=repository,
                )

            self.assertIn("VECTOR(1024)", str(raised.exception))
            self.assertEqual(repository.saved, {})

        asyncio.run(scenario())

    def test_wrong_vector_from_provider_is_rejected_before_repository(self) -> None:
        async def scenario() -> None:
            job_manager = Mock()
            job_manager.get_job.return_value = SimpleNamespace(
                status="completed",
                result=_ocr_result(),
            )
            repository = FakeRepository()
            embedder = FakeEmbedder(vector_dimension=128)

            with self.assertRaises(EmbeddingValidationError) as raised:
                await save_ocr_result_with_embeddings(
                    OcrVectorSaveRequest(jobId="completed-job"),
                    Mock(spec=Session),
                    job_manager=job_manager,
                    embedder=embedder,  # type: ignore[arg-type]
                    repository=repository,
                )

            self.assertIn("Chunk 0", str(raised.exception))
            self.assertIn("128", str(raised.exception))
            self.assertEqual(repository.saved, {})

        asyncio.run(scenario())

    def test_embedding_failure_stops_before_db_save(self) -> None:
        async def scenario() -> None:
            job_manager = Mock()
            job_manager.get_job.return_value = SimpleNamespace(
                status="completed",
                result=_ocr_result(),
            )
            repository = FakeRepository()
            embedder = FakeEmbedder(error=EmbeddingGenerationError("실패"))

            with self.assertRaises(EmbeddingGenerationError):
                await save_ocr_result_with_embeddings(
                    OcrVectorSaveRequest(jobId="completed-job"),
                    Mock(spec=Session),
                    job_manager=job_manager,
                    embedder=embedder,  # type: ignore[arg-type]
                    repository=repository,
                )
            self.assertEqual(repository.saved, {})

        asyncio.run(scenario())

    def test_incomplete_job_is_rejected(self) -> None:
        job_manager = Mock()
        job_manager.get_job.return_value = SimpleNamespace(status="processing", result=None)
        with self.assertRaises(OcrSaveValidationError):
            asyncio.run(
                save_ocr_result_with_embeddings(
                    OcrVectorSaveRequest(jobId="processing-job"),
                    Mock(spec=Session),
                    job_manager=job_manager,
                )
            )

    def test_original_file_reference_falls_back_within_column_length(self) -> None:
        reference = _build_job_file_reference("job-id", "가" * 600 + ".pdf")
        self.assertTrue(reference.startswith("ocr-job://job-id/"))
        self.assertLessEqual(len(reference), 500)

    def test_url_job_keeps_existing_embedding_flow_and_saves_final_url(self) -> None:
        async def scenario() -> None:
            job_manager = Mock()
            url_result = _ocr_result().model_copy(
                update={
                    "source_type": "url",
                    "source_url": "https://example.com/final",
                }
            )
            job_manager.get_job.return_value = SimpleNamespace(
                status="completed", result=url_result
            )
            embedder = FakeEmbedder()
            repository = FakeRepository()

            await save_ocr_result_with_embeddings(
                OcrVectorSaveRequest(jobId="url-job"),
                Mock(spec=Session),
                job_manager=job_manager,
                embedder=embedder,  # type: ignore[arg-type]
                repository=repository,
            )

            self.assertEqual(embedder.received_chunks, ["첫 Chunk", "둘째 Chunk"])
            self.assertEqual(
                repository.saved["original_file_url"],
                "https://example.com/final",
            )

        asyncio.run(scenario())


class OcrVectorSaveApiTest(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.api.admin.router import router
        from app.core.database import get_db

        app = FastAPI()
        app.include_router(router, prefix="/api/admin")
        app.dependency_overrides[get_db] = lambda: Mock(spec=Session)
        self.client = TestClient(app)

    def test_success_response_uses_camel_case_contract(self) -> None:
        document_id = uuid4()
        result = {
            "message": "저장 완료",
            "documentId": document_id,
            "chunkCount": 2,
            "embeddingProvider": "gemini",
            "embeddingDimension": 1024,
            "embeddingModel": "gemini-embedding-001",
        }
        with patch(
            "app.api.admin.router.save_ocr_result_with_embeddings",
            new=AsyncMock(return_value=result),
        ):
            response = self.client.post(
                "/api/admin/ocr/vector-save",
                json={"jobId": "completed-job"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["documentId"], str(document_id))
        self.assertEqual(response.json()["embeddingProvider"], "gemini")
        self.assertEqual(response.json()["embeddingDimension"], 1024)

    def test_embedding_failure_is_not_reported_as_success(self) -> None:
        with patch(
            "app.api.admin.router.save_ocr_result_with_embeddings",
            new=AsyncMock(side_effect=EmbeddingGenerationError("Embedding 생성 실패")),
        ):
            response = self.client.post(
                "/api/admin/ocr/vector-save",
                json={"jobId": "completed-job"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "Embedding 생성 실패")

    def test_db_failure_is_not_reported_as_success(self) -> None:
        with patch(
            "app.api.admin.router.save_ocr_result_with_embeddings",
            new=AsyncMock(side_effect=DocumentPersistenceError("Neon 저장 실패")),
        ):
            response = self.client.post(
                "/api/admin/ocr/vector-save",
                json={"jobId": "completed-job"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Neon 저장 실패")


class FakeSession:
    def __init__(self, *, document_id, fail_commit: bool = False) -> None:
        self.document_id = document_id
        self.fail_commit = fail_commit
        self.document: Any | None = None
        self.chunk_rows = []
        self.committed = False
        self.rolled_back = False

    def add(self, value) -> None:
        self.document = value

    def flush(self) -> None:
        if self.document is None:
            raise AssertionError("flush 전에 document가 추가되어야 합니다.")
        self.document.id = self.document_id

    def add_all(self, values) -> None:
        self.chunk_rows = list(values)

    def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("DB unavailable")
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class FakeEmbedder:
    provider = "fake"
    model = "fake-embedding"

    def __init__(
        self,
        error: Exception | None = None,
        *,
        dimension: int = 1024,
        vector_dimension: int | None = None,
    ) -> None:
        self.error = error
        self.dimension = dimension
        self.vector_dimension = vector_dimension or dimension
        self.received_chunks = []

    async def embed_chunks(self, chunks):
        self.received_chunks = chunks
        if self.error:
            raise self.error
        return [
            [float(index)] * self.vector_dimension
            for index, _chunk in enumerate(chunks)
        ]


class FakeRepository:
    def __init__(self) -> None:
        self.saved = {}
        self.result = SavedDocument(document_id=uuid4(), chunk_count=2)

    def save_with_chunks(self, **kwargs):
        self.saved = kwargs
        return self.result


def _embedding_service(client_factory) -> GeminiEmbeddingService:
    return GeminiEmbeddingService(
        api_key="test-api-key",
        model="gemini-embedding-001",
        dimension=1024,
        timeout_seconds=5,
        client_factory=client_factory,
    )


def _embedding_settings(*, embedding_provider: str) -> Settings:
    return Settings(
        embedding_provider=embedding_provider,
        embedding_model="gemini-embedding-001",
        embedding_dimension=1024,
        embedding_timeout_seconds=5,
        gemini_api_key="test-api-key",
    )


def _client_factory(response):
    def create(_api_key):
        return SimpleNamespace(
            aio=SimpleNamespace(
                models=SimpleNamespace(embed_content=AsyncMock(return_value=response)),
                aclose=AsyncMock(),
            ),
            close=Mock(),
        )

    return create


def _ocr_result() -> OcrDocumentResponse:
    return OcrDocumentResponse(
        documentName="sample.pdf",
        pageCount=1,
        characterCount=16,
        estimatedChunks=2,
        confidence=99.0,
        extractedText="첫 Chunk\n둘째 Chunk",
        chunks=["첫 Chunk", "둘째 Chunk"],
        readiness="ready",
        notes=[],
    )


if __name__ == "__main__":
    unittest.main()
