"""Cloud Run 본문 크기 제한을 우회하는 관리자 R2 직접 업로드 API입니다."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.auth.dependencies import require_admin
from app.models.generated import Users
from app.schemas.admin import (
    OcrJobCreatedResponse,
    OcrMultipartPartUrlRequest,
    OcrMultipartPartUrlResponse,
    OcrMultipartUploadAbortRequest,
    OcrMultipartUploadCompleteRequest,
    OcrMultipartUploadCompleteResponse,
    OcrMultipartUploadInitRequest,
    OcrMultipartUploadInitResponse,
    OcrRemoteJobRequest,
)
from app.services.large_upload_service import (
    LargeUploadValidationError,
    large_upload_service,
)
from app.services.ocr_job_service import OcrJobCapacityError, ocr_job_manager
from app.services.r2_storage import R2StorageError

router = APIRouter()
AdminUser = Annotated[Users, Depends(require_admin)]


@router.post("/ocr/uploads/init", response_model=OcrMultipartUploadInitResponse)
def initiate_upload(
    payload: OcrMultipartUploadInitRequest,
    _admin: AdminUser,
) -> OcrMultipartUploadInitResponse:
    try:
        return OcrMultipartUploadInitResponse.model_validate(
            large_upload_service.initiate(
                payload.file_name,
                payload.file_size,
                payload.content_type,
            )
        )
    except LargeUploadValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except R2StorageError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.post("/ocr/uploads/part-url", response_model=OcrMultipartPartUrlResponse)
def create_part_url(
    payload: OcrMultipartPartUrlRequest,
    _admin: AdminUser,
) -> OcrMultipartPartUrlResponse:
    try:
        url = large_upload_service.create_part_url(
            payload.object_key,
            payload.upload_id,
            payload.part_number,
        )
        return OcrMultipartPartUrlResponse(uploadUrl=url)
    except LargeUploadValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except R2StorageError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.post("/ocr/uploads/complete", response_model=OcrMultipartUploadCompleteResponse)
def complete_upload(
    payload: OcrMultipartUploadCompleteRequest,
    _admin: AdminUser,
) -> OcrMultipartUploadCompleteResponse:
    try:
        return OcrMultipartUploadCompleteResponse.model_validate(
            large_upload_service.complete(
                object_key=payload.object_key,
                upload_id=payload.upload_id,
                file_size=payload.file_size,
                parts=payload.parts,
            )
        )
    except LargeUploadValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except R2StorageError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.post("/ocr/uploads/abort", status_code=status.HTTP_204_NO_CONTENT)
def abort_upload(payload: OcrMultipartUploadAbortRequest, _admin: AdminUser) -> Response:
    try:
        large_upload_service.abort(payload.object_key, payload.upload_id)
    except LargeUploadValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except R2StorageError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/ocr/jobs/remote",
    response_model=OcrJobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_remote_ocr_job(
    payload: OcrRemoteJobRequest,
    _admin: AdminUser,
) -> OcrJobCreatedResponse:
    try:
        return await ocr_job_manager.create_remote_job(
            object_key=payload.object_key,
            file_name=payload.file_name,
            file_size=payload.file_size,
            content_type=payload.content_type,
            chunk_size=payload.chunk_size,
            overlap=payload.overlap,
        )
    except OcrJobCapacityError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc
