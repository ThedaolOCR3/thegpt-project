"""OCR 및 PDF 추출 텍스트를 RAG 입력에 적합한 최소 형태로 정리합니다."""

import re
import unicodedata

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
EXCESSIVE_BLANK_LINES = re.compile(r"\n{3,}")
TRAILING_SPACES = re.compile(r"[ \t]+\n")


def clean_document_text(text: str) -> str:
    """원문 의미는 바꾸지 않고 제어문자와 과도한 공백만 제거합니다."""

    normalized = unicodedata.normalize("NFKC", text.replace("\r\n", "\n"))
    without_controls = CONTROL_CHARACTERS.sub("", normalized)
    without_trailing_spaces = TRAILING_SPACES.sub("\n", without_controls)
    return EXCESSIVE_BLANK_LINES.sub("\n\n", without_trailing_spaces).strip()
