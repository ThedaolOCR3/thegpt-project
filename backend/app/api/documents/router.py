from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.auth.dependencies import get_current_user
from app.core.logging import get_logger
from app.models.generated import Users
from app.schemas.document import OcrLineResponse, OcrResponse

router = APIRouter()
logger = get_logger("api.documents")

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/ocr", response_model=OcrResponse)
async def extract_text(
    file: UploadFile,
    current_user: Annotated[Users, Depends(get_current_user)],
) -> OcrResponse:
    """업로드한 이미지에서 텍스트를 추출한다 (채팅 첨부파일 미리보기 패널에서 호출).

    파일을 저장하지는 않는다 — OCR 결과만 즉시 반환하고 끝. 원본을 서버에 남겨야
    하면 Object Storage 연동 후 여기서 업로드까지 같이 처리하면 된다.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "지원하지 않는 파일 형식입니다.")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "파일이 너무 큽니다 (최대 10MB).")

    try:
        from ai.ocr import run_ocr
    except ImportError:
        logger.exception("ai.ocr import 실패 — ai/ocr/requirements.txt 설치 필요")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "OCR 기능을 사용할 수 없습니다.") from None

    try:
        result = run_ocr(image_bytes)
    except Exception:
        logger.exception("OCR 처리 실패: user_id=%s file=%s", current_user.id, file.filename)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "텍스트 추출에 실패했습니다.") from None

    return OcrResponse(
        text=result.text,
        lines=[OcrLineResponse(text=l.text, confidence=l.confidence) for l in result.lines],
    )
