"""Admin OCR의 VectorDB 저장 Mock 동작만 유지합니다."""

import logging

from app.schemas.admin import (
    VectorSaveTestRequest,
    VectorSaveTestResponse,
)

logger = logging.getLogger(__name__)


async def save_document_test(request: VectorSaveTestRequest) -> VectorSaveTestResponse:
    """DB Side Effect 없이 VectorDB 저장 사용자 흐름만 확인합니다."""

    logger.info("[AdminOCR] Vector save mock completed for %s", request.document_name)
    return VectorSaveTestResponse(
        message="(backend)저장 테스트가 완료되었습니다. 실제 VectorDB에는 저장되지 않았습니다."
    )
