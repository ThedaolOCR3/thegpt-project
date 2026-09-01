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
    EmbeddingBatch,
    EmbeddingGenerationError,
    EmbeddingValidationError,
    RemoteDualEmbeddingService,
    create_embedding_service,
)


class RemoteDualEmbeddingServiceTest(unittest.TestCase):
    def test_settings_create_jina_and_bge_service(self) -> None:
        service = create_embedding_service(_embedding_settings())

        self.assertIsInstance(service, RemoteDualEmbeddingService)
        self.assertEqual(service.provider, "remote-dual")
        self.assertEqual(service.models, ("jina-v4", "medical-bgem3"))
        self.assertEqual(service.dimension, 1024)

    def test_empty_chunk_is_rejected_before_remote_call(self) -> None:
        service = create_embedding_service(_embedding_settings())
        with self.assertRaises(EmbeddingValidationError):
            asyncio.run(service.embed_chunks(["정상", "  "]))


class DocumentRepositoryTest(unittest.TestCase):
    def test_document_and_all_chunks_are_committed_together(self) -> None:
        document_id = uuid4()
        db = FakeSession(document_id=document_id)
        repository = DocumentRepository(db)  # type: ignore[arg-type]

        saved = repository.save_with_chunks(
            original_file_url="ocr-job://job/sample.pdf",
            extracted_text="전체 텍스트",
            chunks=["첫 Chunk", "둘째 Chunk"],
            embeddings_by_provider={
                "jina-v4": [[0.1] * 1024, [0.2] * 1024],
                "medical-bgem3": [[0.3] * 1024, [0.4] * 1024],
            },
        )

        self.assertEqual(saved, SavedDocument(document_id=document_id, chunk_count=2))
        self.assertTrue(db.committed)
        self.assertFalse(db.rolled_back)
        self.assertEqual([row.chunk_index for row in db.chunk_rows], [0, 1])
        self.assertTrue(all(row.document_id == document_id for row in db.chunk_rows))
        self.assertEqual([row.chunk_text for row in db.chunk_rows], ["첫 Chunk", "둘째 Chunk"])
        self.assertEqual(len(db.embedding_rows), 4)
        self.assertEqual(
            {row.provider_name for row in db.embedding_rows},
            {"jina-v4", "medical-bgem3"},
        )
        self.assertTrue(all(row.dimension == 1024 for row in db.embedding_rows))
        self.assertTrue(all(len(row.embedding) == 2048 for row in db.embedding_rows))

    def test_db_failure_rolls_back_whole_save(self) -> None:
        db = FakeSession(document_id=uuid4(), fail_commit=True)
        repository = DocumentRepository(db)  # type: ignore[arg-type]

        with self.assertRaises(DocumentPersistenceError):
            repository.save_with_chunks(
                original_file_url="ocr-job://job/sample.pdf",
                extracted_text="전체 텍스트",
                chunks=["Chunk"],
                embeddings_by_provider={
                    "jina-v4": [[0.1] * 1024],
                    "medical-bgem3": [[0.2] * 1024],
                },
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
            self.assertEqual(response.embedding_provider, "remote-dual")
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
            "embeddingProvider": "remote-dual",
            "embeddingDimension": 1024,
            "embeddingModel": "jina-v4 + medical-bgem3",
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
        self.assertEqual(response.json()["embeddingProvider"], "remote-dual")
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
        self.embedding_rows = []
        self.committed = False
        self.rolled_back = False
        self.flush_count = 0

    def add(self, value) -> None:
        self.document = value

    def flush(self) -> None:
        if self.document is None:
            raise AssertionError("flush 전에 document가 추가되어야 합니다.")
        self.flush_count += 1
        if self.flush_count == 1:
            self.document.id = self.document_id
            return
        for row in self.chunk_rows:
            row.id = uuid4()

    def add_all(self, values) -> None:
        rows = list(values)
        if not self.chunk_rows:
            self.chunk_rows = rows
        else:
            self.embedding_rows = rows

    def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("DB unavailable")
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class FakeEmbedder:
    provider = "remote-dual"
    model = "jina-v4 + medical-bgem3"
    models = ("jina-v4", "medical-bgem3")

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
        vectors = [
            [float(index)] * self.vector_dimension
            for index, _chunk in enumerate(chunks)
        ]
        return EmbeddingBatch(
            vectors_by_provider={
                "jina-v4": vectors,
                "medical-bgem3": [vector.copy() for vector in vectors],
            }
        )


class FakeRepository:
    def __init__(self) -> None:
        self.saved = {}
        self.result = SavedDocument(document_id=uuid4(), chunk_count=2)

    def save_with_chunks(self, **kwargs):
        self.saved = kwargs
        return self.result


def _embedding_settings() -> Settings:
    return Settings(
        _env_file=None,
        embedding_remote_base_url="https://embedding.test",
        embedding_api_key="test-api-key",
        embedding_jina_model="jina-v4",
        embedding_bge_model="medical-bgem3",
        embedding_dimension=1024,
        embedding_timeout_seconds=5,
        embedding_batch_size=32,
    )


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
