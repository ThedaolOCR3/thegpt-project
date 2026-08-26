from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.auth.dependencies import get_current_user
from app.core.logging import get_logger
from app.models.generated import Users
from app.schemas.document import OcrLineResponse, OcrResponse
from app.services.hybrid_ocr.document_processing_service import process_document
from app.services.hybrid_ocr.errors import (
    DocumentProcessingError,
    DocumentTooLargeError,
    DocumentValidationError,
    OcrUnavailableError,
)

router = APIRouter()
logger = get_logger("api.documents")

# hybrid_ocr(csj-ocr 브랜치에서 이식)로 이미지/PDF/DOCX/PPTX를 직접 추출한다.
# 파일 크기·페이지 수 등 검증 기준은 core/config.py의 ocr_* 설정을 따른다.
# RAG 청킹용 chunk_size/overlap은 채팅 미리보기에서는 굳이 노출하지 않고 기본값으로 고정.
_DEFAULT_CHUNK_SIZE = 512
_DEFAULT_CHUNK_OVERLAP = 50


@router.post("/ocr", response_model=OcrResponse)
async def extract_text(
    file: UploadFile,
    current_user: Annotated[Users, Depends(get_current_user)],
) -> OcrResponse:
    """업로드한 문서에서 텍스트를 추출한다 (채팅 첨부파일 미리보기 패널에서 호출).

    파일을 저장하지는 않는다 — OCR 결과만 즉시 반환하고 끝. 원본을 서버에 남겨야
    하면 Object Storage(R2) 연동 후 여기서 업로드까지 같이 처리하면 된다.
    """
    try:
        result = await process_document(
            file=file,
            chunk_size=_DEFAULT_CHUNK_SIZE,
            overlap=_DEFAULT_CHUNK_OVERLAP,
        )
    except DocumentTooLargeError as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except DocumentValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except OcrUnavailableError as exc:
        logger.exception("OCR 엔진을 사용할 수 없습니다.")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except DocumentProcessingError as exc:
        logger.exception("OCR 처리 실패: user_id=%s file=%s", current_user.id, file.filename)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "텍스트 추출에 실패했습니다.") from exc

    # OcrDocumentResponse(관리자 대시보드용 상세 스키마)를 기존 채팅 계약(OcrResponse)으로
    # 축약한다 — 프론트엔드는 text만 실제로 쓰고 있어서, chunks/신뢰도는 line 하나로 합쳐 전달.
    lines = (
        [OcrLineResponse(text=result.extracted_text, confidence=result.confidence / 100, page=0)]
        if result.extracted_text
        else []
    )
    return OcrResponse(text=result.extracted_text, lines=lines)
