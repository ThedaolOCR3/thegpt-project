import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.repositories.document_repository import SavedDocument
from app.schemas.admin import OcrDocumentResponse, OcrVectorSaveRequest
from app.services.admin_ocr import save_ocr_result_with_embeddings
from app.services.embedding_service import EmbeddingBatch


class LargeOcrVectorSaveTest(unittest.TestCase):
    def test_artifact_chunks_are_embedded_and_saved_in_batches(self) -> None:
        async def scenario() -> None:
            chunks = [f"Chunk {index}" for index in range(35)]
            storage = FakeArtifactStorage(chunks)
            repository = FakeStagedRepository()
            embedder = FakeBatchEmbedder()
            job_manager = Mock()
            job_manager.get_job.return_value = SimpleNamespace(
                status="completed",
                result=OcrDocumentResponse(
                    documentName="data.jsonl",
                    pageCount=None,
                    characterCount=350,
                    estimatedChunks=len(chunks),
                    confidence=100,
                    extractedText="preview",
                    chunks=chunks[:20],
                    readiness="ready",
                    notes=[],
                    chunk_artifact_key="admin-rag-artifacts/chunks.jsonl",
                    original_object_key="admin-rag-uploads/id/data.jsonl",
                ),
            )

            response = await save_ocr_result_with_embeddings(
                OcrVectorSaveRequest(jobId="large-job"),
                Mock(spec=Session),
                job_manager=job_manager,
                embedder=embedder,  # type: ignore[arg-type]
                repository=repository,  # type: ignore[arg-type]
                storage=storage,  # type: ignore[arg-type]
            )

            self.assertEqual(embedder.batch_sizes, [32, 3])
            self.assertEqual(repository.start_indices, [0, 32])
            self.assertEqual(repository.saved_chunks, chunks)
            self.assertEqual(response.chunk_count, 35)
            self.assertEqual(storage.deleted, ["admin-rag-artifacts/chunks.jsonl"])
            self.assertTrue(repository.finished)

        asyncio.run(scenario())


class FakeArtifactStorage:
    def __init__(self, chunks: list[str]) -> None:
        self.content = b"".join(
            json.dumps({"text": chunk}).encode() + b"\n" for chunk in chunks
        )
        self.deleted: list[str] = []

    def iter_object_chunks(self, _key, chunk_size=1024 * 1024):
        for start in range(0, len(self.content), 41):
            yield self.content[start : start + 41]

    def delete_object(self, key):
        self.deleted.append(key)


class FakeStagedRepository:
    def __init__(self) -> None:
        self.document_id = uuid4()
        self.start_indices: list[int] = []
        self.saved_chunks: list[str] = []
        self.finished = False
        self.aborted = False

    def begin_staged_save(self, *, original_file_url, extracted_text):
        self.original_file_url = original_file_url
        self.extracted_text = extracted_text
        return self.document_id

    def append_staged_chunks(
        self,
        *,
        document_id,
        start_index,
        chunks,
        embeddings_by_provider,
    ):
        self.assert_document_id = document_id
        self.start_indices.append(start_index)
        self.saved_chunks.extend(chunks)
        self.embeddings_by_provider = embeddings_by_provider

    def finish_staged_save(self, document_id, chunk_count):
        self.finished = True
        return SavedDocument(document_id=document_id, chunk_count=chunk_count)

    def abort_staged_save(self, _document_id):
        self.aborted = True


class FakeBatchEmbedder:
    provider = "remote-dual"
    model = "jina-v4 + medical-bgem3"
    dimension = 1024

    def __init__(self) -> None:
        self.batch_sizes: list[int] = []

    async def embed_chunks(self, chunks):
        self.batch_sizes.append(len(chunks))
        return EmbeddingBatch(
            vectors_by_provider={
                "jina-v4": [[0.1] * 1024 for _ in chunks],
                "medical-bgem3": [[0.2] * 1024 for _ in chunks],
            }
        )


if __name__ == "__main__":
    unittest.main()
