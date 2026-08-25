"""Hybrid OCR 단계에서 사용하는 도메인 예외를 정의합니다."""


class HybridOcrError(Exception):
    """Hybrid OCR에서 처리 가능한 오류의 공통 부모입니다."""


class DocumentValidationError(HybridOcrError):
    """업로드 문서가 검증 기준을 만족하지 않을 때 발생합니다."""


class DocumentTooLargeError(DocumentValidationError):
    """업로드 문서가 허용 크기를 초과할 때 발생합니다."""


class DocumentProcessingError(HybridOcrError):
    """검증을 마친 문서를 추출하는 중 실패할 때 발생합니다."""


class OfficeExtractionError(DocumentProcessingError):
    """DOCX/PPTX의 OOXML 구조를 직접 추출하지 못했을 때 발생합니다."""


class OcrUnavailableError(HybridOcrError):
    """PaddleOCR 의존성이나 모델을 사용할 수 없을 때 발생합니다."""


class OcrJobNotFoundError(HybridOcrError):
    """요청한 OCR Job이 없거나 만료되었을 때 발생합니다."""


class OcrJobCapacityError(HybridOcrError):
    """동시에 보관할 수 있는 OCR Job 수를 초과했을 때 발생합니다."""
