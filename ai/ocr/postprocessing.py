"""OCR 결과 후처리 — 신뢰도 낮은 라인 제거, 중복 줄 정리, 공백/개행 정리."""
import re
from dataclasses import dataclass


@dataclass
class OcrLine:
    text: str
    confidence: float
    page: int = 0  # 단일 이미지는 항상 0. PDF는 페이지 인덱스(0부터).


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _dedupe_consecutive(lines: list[str]) -> list[str]:
    """겹치는 감지 박스 때문에 PaddleOCR이 같은 줄을 연달아 두 번 뱉는 경우가 있어 정리한다."""
    result: list[str] = []
    for line in lines:
        if not result or result[-1] != line:
            result.append(line)
    return result


def postprocess(lines: list[OcrLine], min_confidence: float = 0.5) -> str:
    """신뢰도가 min_confidence 미만인 라인은 버리고, 남은 라인을 페이지 단위로 합친다.

    여러 페이지(PDF)가 섞여 있으면 페이지 사이에 구분선을 넣는다 — 단일 이미지처럼
    페이지가 하나뿐이면 기존과 동일하게 구분선 없이 이어붙인다.
    """
    kept = [line for line in lines if line.confidence >= min_confidence]
    if not kept:
        return ""

    pages = sorted({line.page for line in kept})
    if len(pages) <= 1:
        return clean_text("\n".join(_dedupe_consecutive([line.text for line in kept])))

    page_texts = []
    for page in pages:
        page_lines = [line.text for line in kept if line.page == page]
        page_texts.append(clean_text("\n".join(_dedupe_consecutive(page_lines))))

    return "\n\n".join(f"--- 페이지 {page + 1} ---\n{text}" for page, text in zip(pages, page_texts))
