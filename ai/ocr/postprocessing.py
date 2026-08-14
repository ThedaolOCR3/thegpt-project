"""OCR 결과 후처리 — 신뢰도 낮은 라인 제거, 공백/개행 정리."""
import re
from dataclasses import dataclass


@dataclass
class OcrLine:
    text: str
    confidence: float


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def postprocess(lines: list[OcrLine], min_confidence: float = 0.5) -> str:
    """신뢰도가 min_confidence 미만인 라인은 버리고, 남은 라인을 줄바꿈으로 합친다."""
    kept = [line.text for line in lines if line.confidence >= min_confidence]
    return clean_text("\n".join(kept))
