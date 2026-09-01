import asyncio
import io
import unittest
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile

from app.schemas.admin import OcrMultipartCompletedPart
from app.services.large_document_service import LargeDocumentService, iter_chunk_artifact
from app.services.large_upload_service import (
    MIB,
    UPLOAD_PART_SIZE_BYTES,
    LargeUploadService,
    LargeUploadValidationError,
)


class LargeUploadServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = FakeStorage()
        self.service = LargeUploadService(self.storage, _settings())  # type: ignore[arg-type]

    def test_exactly_eight_gib_is_split_into_128_parts(self) -> None:
        result = self.service.initiate("대용량 데이터.jsonl", 8 * 1024**3, "application/x-ndjson")

        self.assertEqual(result["partSize"], 64 * MIB)
        self.assertEqual(result["partCount"], 128)
        self.assertTrue(result["objectKey"].endswith("/대용량_데이터.jsonl"))

    def test_file_larger_than_eight_gib_is_rejected(self) -> None:
        with self.assertRaises(LargeUploadValidationError):
            self.service.initiate("too-large.txt", 8 * 1024**3 + 1, "text/plain")

    def test_complete_requires_every_part_and_verifies_size(self) -> None:
        file_size = UPLOAD_PART_SIZE_BYTES + 10
        self.storage.head_size = file_size
        parts = [
            OcrMultipartCompletedPart(partNumber=2, etag="etag-2"),
            OcrMultipartCompletedPart(partNumber=1, etag="etag-1"),
        ]

        result = self.service.complete(
            object_key="admin-rag-uploads/id/data.txt",
            upload_id="upload-id",
            file_size=file_size,
            parts=parts,
        )

        self.assertEqual(result["fileSize"], file_size)
        self.assertEqual(
            self.storage.completed_parts,
            [
                {"PartNumber": 1, "ETag": "etag-1"},
                {"PartNumber": 2, "ETag": "etag-2"},
            ],
        )

    def test_size_mismatch_deletes_completed_object(self) -> None:
        self.storage.head_size = 3
        with self.assertRaises(LargeUploadValidationError):
            self.service.complete(
                object_key="admin-rag-uploads/id/data.txt",
                upload_id="upload-id",
                file_size=4,
                parts=[OcrMultipartCompletedPart(partNumber=1, etag="etag")],
            )
        self.assertEqual(self.storage.deleted, ["admin-rag-uploads/id/data.txt"])


class LargeDocumentServiceTest(unittest.TestCase):
    def test_text_is_streamed_to_chunk_artifact_and_only_preview_is_returned(self) -> None:
        content = ("가나다라마바사아자차카타파하\n" * 30).encode()
        storage = FakeStorage({"admin-rag-uploads/id/data.txt": content})
        service = LargeDocumentService(storage, _settings())  # type: ignore[arg-type]

        result = asyncio.run(
            service.process(
                object_key="admin-rag-uploads/id/data.txt",
                file_name="data.txt",
                file_size=len(content),
                content_type="text/plain",
                chunk_size=50,
                overlap=5,
            )
        )

        self.assertGreater(result.estimated_chunks, 1)
        self.assertEqual(
            len(list(iter_chunk_artifact(result.chunk_artifact_key or "", storage))),
            result.estimated_chunks,
        )
        self.assertEqual(result.original_object_key, "admin-rag-uploads/id/data.txt")
        serialized = result.model_dump(by_alias=True)
        self.assertNotIn("chunk_artifact_key", serialized)
        self.assertNotIn("original_object_key", serialized)

    def test_zip_text_member_is_read_through_range_requests(self) -> None:
        archive_buffer = io.BytesIO()
        with ZipFile(archive_buffer, "w", ZIP_DEFLATED) as archive:
            archive.writestr("folder/records.jsonl", '{"id": 1}\n{"id": 2}\n')
            archive.writestr("ignored.bin", b"binary")
        content = archive_buffer.getvalue()
        key = "admin-rag-uploads/id/archive.zip"
        storage = FakeStorage({key: content})
        service = LargeDocumentService(storage, _settings())  # type: ignore[arg-type]

        result = asyncio.run(
            service.process(
                object_key=key,
                file_name="archive.zip",
                file_size=len(content),
                content_type="application/zip",
                chunk_size=50,
                overlap=5,
            )
        )

        self.assertIn("records.jsonl", result.extracted_text)
        self.assertTrue(any("건너뛰" in note for note in result.notes))
        self.assertGreater(storage.range_request_count, 0)


class FakeStorage:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = dict(objects or {})
        self.multipart: dict[tuple[str, str], dict[int, bytes]] = {}
        self.head_size = -1
        self.completed_parts = []
        self.deleted: list[str] = []
        self.range_request_count = 0

    def create_multipart_upload(self, *, key, content_type, file_name, file_size):
        del content_type, file_name, file_size
        upload_id = f"upload-{len(self.multipart) + 1}"
        self.multipart[(key, upload_id)] = {}
        return upload_id

    def presign_upload_part(self, **kwargs):
        return f"https://upload.test/{kwargs['part_number']}"

    def upload_part(self, *, key, upload_id, part_number, content):
        self.multipart[(key, upload_id)][part_number] = content
        return f"etag-{part_number}"

    def complete_multipart_upload(self, *, key, upload_id, parts):
        self.completed_parts = parts
        stored_parts = self.multipart.get((key, upload_id))
        if stored_parts is not None:
            self.objects[key] = b"".join(stored_parts[index] for index in sorted(stored_parts))
        return "completed-etag"

    def abort_multipart_upload(self, *, key, upload_id):
        self.multipart.pop((key, upload_id), None)

    def head_object(self, key):
        size = len(self.objects[key]) if key in self.objects else self.head_size
        return {"ContentLength": size}

    def delete_object(self, key):
        self.objects.pop(key, None)
        self.deleted.append(key)

    def iter_object_chunks(self, key, chunk_size=1024 * 1024):
        content = self.objects[key]
        for start in range(0, len(content), chunk_size):
            yield content[start : start + chunk_size]

    def get_object_range(self, key, start, end):
        self.range_request_count += 1
        return self.objects[key][start : end + 1]


def _settings():
    return SimpleNamespace(
        ocr_max_file_size_mb=8 * 1024,
        ocr_inline_file_size_mb=20,
        ocr_large_archive_uncompressed_size_mb=16 * 1024,
        ocr_max_office_archive_entries=5_000,
    )


if __name__ == "__main__":
    unittest.main()
