import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin.upload_router import router
from app.api.auth.dependencies import require_admin


class AdminLargeUploadApiTest(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/admin")
        app.dependency_overrides[require_admin] = lambda: SimpleNamespace(is_admin=True)
        self.client = TestClient(app)

    def test_init_response_uses_camel_case_contract(self) -> None:
        result = {
            "uploadId": "upload-id",
            "objectKey": "admin-rag-uploads/id/data.txt",
            "partSize": 64 * 1024**2,
            "partCount": 2,
        }
        with patch(
            "app.api.admin.upload_router.large_upload_service.initiate",
            return_value=result,
        ):
            response = self.client.post(
                "/api/admin/ocr/uploads/init",
                json={"fileName": "data.txt", "fileSize": 70 * 1024**2, "contentType": "text/plain"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), result)

    def test_request_over_eight_gib_is_rejected_by_schema(self) -> None:
        response = self.client.post(
            "/api/admin/ocr/uploads/init",
            json={"fileName": "data.txt", "fileSize": 8 * 1024**3 + 1, "contentType": "text/plain"},
        )
        self.assertEqual(response.status_code, 422)

    def test_completed_upload_can_start_remote_job(self) -> None:
        with patch(
            "app.api.admin.upload_router.ocr_job_manager.create_remote_job",
            new=AsyncMock(return_value={"jobId": "job-id", "status": "queued"}),
        ):
            response = self.client.post(
                "/api/admin/ocr/jobs/remote",
                json={
                    "objectKey": "admin-rag-uploads/id/data.txt",
                    "fileName": "data.txt",
                    "fileSize": 100,
                    "contentType": "text/plain",
                    "chunkSize": 512,
                    "overlap": 50,
                },
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"jobId": "job-id", "status": "queued"})


if __name__ == "__main__":
    unittest.main()
