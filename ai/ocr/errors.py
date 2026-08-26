"""HTTP 상태 코드와 분리된 OCR Domain 예외를 정의합니다."""


class OcrError(Exception):
    """공통 OCR Core에서 처리 가능한 오류의 부모입니다."""


class DocumentValidationError(OcrError):
    """입력 문서가 검증 기준을 만족하지 않을 때 발생합니다."""


class DocumentTooLargeError(DocumentValidationError):
    """입력 문서가 허용 크기를 초과할 때 발생합니다."""


class DocumentProcessingError(OcrError):
    """검증된 문서의 Text 또는 Image를 추출하지 못했을 때 발생합니다."""


class OfficeExtractionError(DocumentProcessingError):
    """DOCX/PPTX의 OOXML 구조를 직접 추출하지 못했을 때 발생합니다."""


class OcrUnavailableError(OcrError):
    """PaddleOCR 의존성이나 모델을 사용할 수 없을 때 발생합니다."""
