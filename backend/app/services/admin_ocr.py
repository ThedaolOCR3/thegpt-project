"""Admin OCR 요청의 검증, Mock 생성, 응답 조립 순서를 관리합니다."""

import logging
from pathlib import Path

from fastapi import HTTPException, status

from app.schemas.admin import (
    OcrAnalyzeRequest,
    OcrDocumentResponse,
    VectorSaveTestRequest,
    VectorSaveTestResponse,
)

logger = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


async def analyze_document(request: OcrAnalyzeRequest) -> OcrDocumentResponse:
    """Request → 검증 → Mock OCR → Response의 전체 실행 순서를 관리합니다."""

    validated_request = validate_ocr_request(request)

    # 실제 OCR 엔진이 준비되면 아래 Mock 생성 호출만 실제 OCR 호출로 교체합니다.
    mock_result = create_mock_ocr_result(validated_request)

    response = build_ocr_response(mock_result)
    logger.info("[AdminOCR] Mock response created for %s", validated_request.document_name)
    return response


async def save_document_test(request: VectorSaveTestRequest) -> VectorSaveTestResponse:
    """DB Side Effect 없이 VectorDB 저장 사용자 흐름만 확인합니다."""

    logger.info("[AdminOCR] Vector save mock completed for %s", request.document_name)
    return VectorSaveTestResponse(
        message="(backend)저장 테스트가 완료되었습니다. 실제 VectorDB에는 저장되지 않았습니다."
    )


def validate_ocr_request(request: OcrAnalyzeRequest) -> OcrAnalyzeRequest:
    """파일 본문을 읽지 않고 이름과 메타데이터만 검증합니다."""

    extension = Path(request.document_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="PDF, PNG, JPG 형식만 문서 분석 테스트에 사용할 수 있습니다.",
        )
    return request


def create_mock_ocr_result(request: OcrAnalyzeRequest) -> dict[str, object]:
    """향후 실제 OCR 함수로 교체할 단일 Mock 처리 지점입니다."""

    is_pdf = Path(request.document_name).suffix.lower() == ".pdf"
    return {
        "document_name": request.document_name,
        "page_count": 4 if is_pdf else 1,
        "character_count": 4_286 if is_pdf else 1_248,
        "estimated_chunks": 11 if is_pdf else 4,
        "confidence": 94.8 if is_pdf else 97.2,
        "extracted_text": (
            "(backend_mock)"
            "환자의 현재 증상과 과거 병력을 함께 검토해야 합니다. "
            "문서에 포함된 검사 결과는 임상적 판단을 보조하기 위한 참고 자료이며, "
            "최종 진단은 의료 전문가의 확인이 필요합니다."
        ),
        "chunks": [
            "(backend_mock)[Chunk 01] 환자의 현재 증상과 과거 병력을 함께 검토해야 합니다.",
            "(backend_mock)[Chunk 02] 최종 진단은 의료 전문가의 확인이 필요합니다.",
        ],
        "readiness": "review" if is_pdf else "ready",
        "notes": (
            ["표가 포함된 페이지는 열 순서를 확인해 주세요.", "개인정보 포함 여부를 검토해 주세요."]
            if is_pdf
            else ["(backend_mock)","이미지 대비가 양호합니다.", "등록 전 추출 문장의 오탈자를 확인해 주세요."]
        ),
    }


def build_ocr_response(mock_result: dict[str, object]) -> OcrDocumentResponse:
    """Mock과 실제 구현 모두 동일한 Frontend 응답 계약을 사용하게 합니다."""

    return OcrDocumentResponse.model_validate(mock_result)
