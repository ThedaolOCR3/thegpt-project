"""긴 OCR 요청의 진행 상태와 결과를 메모리 Job으로 관리합니다."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from threading import RLock
from uuid import uuid4

from fastapi import UploadFile
from starlette.datastructures import Headers

from ai.ocr.contracts import ProgressCallback
from ai.ocr.errors import DocumentTooLargeError, OcrError
from app.core.config import settings
from app.schemas.admin import (
    OcrDocumentResponse,
    OcrJobCreatedResponse,
    OcrJobStatusResponse,
)
from app.services.ocr_workflow import process_document

logger = logging.getLogger(__name__)


class OcrJobNotFoundError(Exception):
    """요청한 OCR Job이 없거나 만료되었을 때 발생합니다."""


class OcrJobCapacityError(Exception):
    """동시에 보관할 수 있는 OCR Job 수를 초과했을 때 발생합니다."""

OcrProcessor = Callable[
    [UploadFile, int, int, ProgressCallback | None],
    Awaitable[OcrDocumentResponse],
]


@dataclass
class OcrJobRecord:
    job_id: str
    status: str
    stage: str
    progress: int
    message: str
    created_at: datetime
    updated_at: datetime
    result: OcrDocumentResponse | None = None
    error: str | None = None


class OcrJobManager:
    """단일 FastAPI 프로세스 안에서 OCR Job 생성·조회·만료를 관리합니다."""

    def __init__(
        self,
        processor: OcrProcessor,
        max_file_bytes: int,
        max_pending_jobs: int,
        ttl_minutes: int,
    ) -> None:
        self.processor = processor
        self.max_file_bytes = max_file_bytes
        self.max_pending_jobs = max_pending_jobs
        self.ttl = timedelta(minutes=ttl_minutes)
        self._jobs: dict[str, OcrJobRecord] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = RLock()

    async def create_job(
        self,
        file: UploadFile,
        chunk_size: int,
        overlap: int,
    ) -> OcrJobCreatedResponse:
        """업로드 내용을 안전하게 복사한 뒤 백그라운드 OCR 작업을 시작합니다."""

        # 요청이 끝나면 원본 UploadFile이 닫히므로 Job용 byte 복사본을 먼저 만듭니다.
        content = await file.read(self.max_file_bytes + 1)
        if len(content) > self.max_file_bytes:
            max_size_mb = self.max_file_bytes // (1024 * 1024)
            raise DocumentTooLargeError(
                f"파일 크기는 {max_size_mb}MB 이하여야 합니다."
            )

        now = datetime.now(UTC)
        job_id = uuid4().hex
        with self._lock:
            self._remove_expired_jobs(now)
            active_job_count = sum(
                job.status in {"queued", "processing"}
                for job in self._jobs.values()
            )
            if active_job_count >= self.max_pending_jobs:
                raise OcrJobCapacityError(
                    "동시에 처리할 수 있는 OCR 작업 수를 초과했습니다. 잠시 후 다시 시도해 주세요."
                )

            self._jobs[job_id] = OcrJobRecord(
                job_id=job_id,
                status="queued",
                stage="queued",
                progress=3,
                message="OCR 작업이 대기열에 등록되었습니다.",
                created_at=now,
                updated_at=now,
            )

        task = asyncio.create_task(
            self._run_job(
                job_id=job_id,
                content=content,
                file_name=file.filename or "",
                content_type=file.content_type or "application/octet-stream",
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )
        with self._lock:
            self._tasks[job_id] = task
        task.add_done_callback(lambda _task: self._discard_task(job_id))

        return OcrJobCreatedResponse(jobId=job_id, status="queued")

    def get_job(self, job_id: str) -> OcrJobStatusResponse:
        """Frontend polling에 사용할 현재 Job 상태의 복사본을 반환합니다."""

        now = datetime.now(UTC)
        with self._lock:
            self._remove_expired_jobs(now)
            job = self._jobs.get(job_id)
            if job is None:
                raise OcrJobNotFoundError("OCR 작업을 찾을 수 없거나 만료되었습니다.")
            return _build_status_response(job)

    async def _run_job(
        self,
        job_id: str,
        content: bytes,
        file_name: str,
        content_type: str,
        chunk_size: int,
        overlap: int,
    ) -> None:
        upload_file = UploadFile(
            file=BytesIO(content),
            filename=file_name,
            headers=Headers({"content-type": content_type}),
        )
        self._update_progress(
            job_id,
            stage="uploading",
            progress=5,
            message="파일 업로드가 완료되었습니다.",
        )

        try:
            result = await self.processor(
                upload_file,
                chunk_size,
                overlap,
                lambda stage, progress, message: self._update_progress(
                    job_id,
                    stage,
                    progress,
                    message,
                ),
            )
        except OcrError as exc:
            logger.warning("OCR Job 실패: job_id=%s, error=%s", job_id, exc)
            self._fail_job(job_id, str(exc))
        except Exception:
            logger.exception("예상하지 못한 OCR Job 오류: job_id=%s", job_id)
            self._fail_job(job_id, "문서 분석 중 예상하지 못한 오류가 발생했습니다.")
        else:
            self._complete_job(job_id, result)
        finally:
            await upload_file.close()

    def _update_progress(
        self,
        job_id: str,
        stage: str,
        progress: int,
        message: str,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status in {"completed", "failed"}:
                return
            job.status = "processing"
            job.stage = stage
            job.progress = max(job.progress, min(progress, 99))
            job.message = message
            job.updated_at = datetime.now(UTC)

    def _complete_job(self, job_id: str, result: OcrDocumentResponse) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "completed"
            job.stage = "completed"
            job.progress = 100
            job.message = "문서 분석이 완료되었습니다."
            job.result = result
            job.updated_at = datetime.now(UTC)

    def _fail_job(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "failed"
            job.stage = "failed"
            job.message = "문서 분석에 실패했습니다."
            job.error = error
            job.updated_at = datetime.now(UTC)

    def _discard_task(self, job_id: str) -> None:
        with self._lock:
            self._tasks.pop(job_id, None)

    def _remove_expired_jobs(self, now: datetime) -> None:
        expired_job_ids = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in {"completed", "failed"} and now - job.updated_at > self.ttl
        ]
        for job_id in expired_job_ids:
            self._jobs.pop(job_id, None)


def _build_status_response(job: OcrJobRecord) -> OcrJobStatusResponse:
    return OcrJobStatusResponse(
        jobId=job.job_id,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        message=job.message,
        result=job.result,
        error=job.error,
    )


ocr_job_manager = OcrJobManager(
    processor=process_document,
    max_file_bytes=settings.ocr_max_file_size_mb * 1024 * 1024,
    max_pending_jobs=settings.ocr_max_pending_jobs,
    ttl_minutes=settings.ocr_job_ttl_minutes,
)
