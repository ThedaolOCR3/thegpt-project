"""PaddleOCR 실행 오케스트레이션. backend/scripts/Colab에서 공통으로 재사용한다."""
from dataclasses import dataclass, field

from .postprocessing import OcrLine, postprocess
from .preprocessing import is_pdf, pdf_to_images, preprocess, preprocess_image

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
    """이미지 또는 PDF 바이트 -> (전처리 -> PaddleOCR -> 후처리)를 거친 최종 텍스트.

    PDF는 페이지별로 렌더링해서 각각 OCR을 돌리고, 결과에 페이지 번호를 붙여 합친다.
    """
    if is_pdf(image_bytes):
        page_images = [preprocess_image(page) for page in pdf_to_images(image_bytes)]
    else:
        page_images = [preprocess(image_bytes)]

    engine = _get_engine()
    lines: list[OcrLine] = []
    for page_index, image in enumerate(page_images):
        for result in engine.predict(image) or []:
            texts = result.get("rec_texts", [])
            scores = result.get("rec_scores", [])
            for t, s in zip(texts, scores):
                lines.append(OcrLine(text=t, confidence=float(s), page=page_index))

    text = postprocess(lines, min_confidence=min_confidence)
    return OcrResult(text=text, lines=lines, min_confidence=min_confidence)
