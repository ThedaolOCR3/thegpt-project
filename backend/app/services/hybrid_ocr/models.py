"""Hybrid OCR 내부 단계 사이에서 전달하는 데이터 구조를 정의합니다."""

from dataclasses import dataclass, field
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image


@dataclass(frozen=True)
class OcrProcessingConfig:
    """문서 검증과 OCR 판단에 사용하는 한곳에 모인 설정입니다."""

    max_file_bytes: int
    max_pdf_pages: int
    native_text_min_chars: int
    significant_image_area_ratio: float
    pdf_render_dpi: int
    max_image_side: int
    max_image_pixels: int
    paddle_device: str
    paddle_language: str


@dataclass(frozen=True)
class ValidatedDocument:
    """서버 검증을 통과해 후속 처리에 안전하게 전달할 문서입니다."""

    file_name: str
    content_type: str
    file_type: str
    content: bytes


@dataclass(frozen=True)
class OcrEngineResult:
    """PaddleOCR의 복잡한 반환값을 상위 서비스용으로 단순화한 결과입니다."""

    text: str
    confidence: float
    line_count: int
    processing_time_seconds: float


class OcrEngine(Protocol):
    """PDF와 이미지 서비스가 사용하는 OCR 엔진의 최소 계약입니다."""

    def extract_text(self, image: "Image") -> OcrEngineResult: ...


@dataclass(frozen=True)
class ExtractedDocument:
    """파일 형식별 처리가 끝난 뒤 중심 서비스로 돌아오는 공통 결과입니다."""

    text: str
    page_count: int
    document_type: str
    ocr_image_count: int
    average_confidence: float
    warnings: list[str] = field(default_factory=list)
