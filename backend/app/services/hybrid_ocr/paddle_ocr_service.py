"""PaddleOCR 모델 초기화, 실행, 결과 변환을 한곳에서 담당합니다."""

import logging
from functools import lru_cache
from threading import Lock
from time import perf_counter
from typing import Any

import numpy as np
from PIL import Image

from app.services.hybrid_ocr.errors import (
    DocumentProcessingError,
    OcrUnavailableError,
)
from app.services.hybrid_ocr.models import OcrEngineResult

logger = logging.getLogger(__name__)


class PaddleOcrService:
    """한 프로세스에서 PaddleOCR 모델을 한 번만 만들어 재사용합니다."""

    def __init__(self, device: str, language: str) -> None:
        self.device = device
        self.language = language
        self._pipeline: Any | None = None
        self._initialization_lock = Lock()
        self._inference_lock = Lock()

    def extract_text(self, image: Image.Image) -> OcrEngineResult:
        pipeline = self._get_pipeline()
        started_at = perf_counter()

        try:
            # Paddle Pipeline은 동시 predict 안전성을 보장하지 않으므로 한 번에 한 요청만 실행합니다.
            with self._inference_lock:
                predictions = pipeline.predict(np.asarray(image))
            text, confidence, line_count = _parse_predictions(predictions)
        except Exception as exc:
            logger.exception("PaddleOCR 실행 중 오류가 발생했습니다.")
            raise DocumentProcessingError("PaddleOCR 텍스트 추출에 실패했습니다.") from exc

        return OcrEngineResult(
            text=text,
            confidence=confidence,
            line_count=line_count,
            processing_time_seconds=round(perf_counter() - started_at, 3),
        )

    def _get_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        with self._initialization_lock:
            if self._pipeline is None:
                self._pipeline = self._create_pipeline()
        return self._pipeline

    def _create_pipeline(self) -> Any:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OcrUnavailableError(
                "PaddleOCR가 설치되지 않아 이미지 문서를 분석할 수 없습니다."
            ) from exc

        options = {
            "lang": self.language,
            "ocr_version": "PP-OCRv5",
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            # Windows CPU의 oneDNN 정적 실행 경로에서 발생하는 PIR 변환 오류를 피합니다.
            "enable_mkldnn": False,
        }

        try:
            logger.info("PaddleOCR 초기화 시작: device=%s", self.device)
            return PaddleOCR(device=self.device, **options)
        except Exception as first_error:
            if self.device.lower() == "cpu":
                raise OcrUnavailableError("PaddleOCR 모델을 초기화하지 못했습니다.") from first_error

            # GPU 설정이 맞지 않는 PC에서도 기능을 사용할 수 있도록 CPU로 한 번 재시도합니다.
            logger.warning("PaddleOCR GPU 초기화 실패, CPU로 재시도합니다.")
            try:
                return PaddleOCR(device="cpu", **options)
            except Exception as cpu_error:
                raise OcrUnavailableError(
                    "PaddleOCR 모델을 GPU와 CPU 모두에서 초기화하지 못했습니다."
                ) from cpu_error


def _parse_predictions(predictions: Any) -> tuple[str, float, int]:
    lines: list[tuple[list[float], str, float]] = []

    for prediction in predictions:
        payload = getattr(prediction, "json", prediction)
        if callable(payload):
            payload = payload()
        if not isinstance(payload, dict):
            continue

        result = payload.get("res", payload)
        texts = list(result.get("rec_texts", []))
        scores = list(result.get("rec_scores", []))
        boxes = list(result.get("rec_boxes", []))

        for index, raw_text in enumerate(texts):
            text = str(raw_text).strip()
            if not text:
                continue
            score = float(scores[index]) if index < len(scores) else 0.0
            box = _box_as_list(boxes[index]) if index < len(boxes) else [0, index, 0, index]
            lines.append((box, text, score))

    # Paddle 결과를 bounding box의 위→아래, 왼쪽→오른쪽 순서로 정렬합니다.
    lines.sort(key=lambda item: (item[0][1], item[0][0]))
    text = "\n".join(item[1] for item in lines)
    confidence = sum(item[2] for item in lines) / len(lines) if lines else 0.0
    return text, confidence, len(lines)


def _box_as_list(box: Any) -> list[float]:
    values = box.tolist() if hasattr(box, "tolist") else list(box)
    if len(values) >= 4:
        return [float(value) for value in values[:4]]
    return [0.0, 0.0, 0.0, 0.0]


@lru_cache(maxsize=4)
def get_paddle_ocr_service(device: str, language: str) -> PaddleOcrService:
    """설정이 같은 요청끼리 모델 인스턴스를 재사용합니다."""

    return PaddleOcrService(device=device, language=language)
