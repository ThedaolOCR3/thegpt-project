"""PaddleOCR 실행 오케스트레이션. backend/scripts/Colab에서 공통으로 재사용한다."""
from dataclasses import dataclass, field

from .postprocessing import OcrLine, postprocess
from .preprocessing import preprocess

_ocr_engine = None


def _get_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR

        # lang="korean": 한국어+영숫자 인식. use_textline_orientation: 세로/180도
        # 회전된 텍스트도 인식(구 API의 use_angle_cls).
        # enable_mkldnn=False: paddlepaddle 3.3.x의 알려진 회귀 버그 회피
        # (oneDNN PIR 실행기가 "ConvertPirAttribute2RuntimeAttribute not support"로
        # 죽는 문제 — PaddlePaddle/Paddle#77340). mkldnn 없이도 CPU 추론엔 문제 없음.
        _ocr_engine = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=True,
            lang="korean",
            enable_mkldnn=False,
        )
    return _ocr_engine


@dataclass
class OcrResult:
    text: str
    lines: list[OcrLine] = field(default_factory=list)
    min_confidence: float = 0.5


def run_ocr(image_bytes: bytes, min_confidence: float = 0.5) -> OcrResult:
    """이미지 바이트 -> (전처리 -> PaddleOCR -> 후처리)를 거친 최종 텍스트."""
    image = preprocess(image_bytes)
    engine = _get_engine()
    pages = engine.predict(image)

    lines: list[OcrLine] = []
    for page in pages or []:
        texts = page.get("rec_texts", [])
        scores = page.get("rec_scores", [])
        for t, s in zip(texts, scores):
            lines.append(OcrLine(text=t, confidence=float(s)))

    text = postprocess(lines, min_confidence=min_confidence)
    return OcrResult(text=text, lines=lines, min_confidence=min_confidence)
