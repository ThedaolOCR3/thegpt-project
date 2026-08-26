import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep

from PIL import Image

from ai.ocr.engine import PaddleOcrService, parse_predictions


class PaddleResultParsingTest(unittest.TestCase):
    def test_box_order_lines_confidence_and_raw_text_are_preserved(self) -> None:
        predictions = [
            {
                "res": {
                    "rec_texts": ["아래", "위", "낮은 신뢰도"],
                    "rec_scores": [0.9, 0.8, 0.2],
                    "rec_boxes": [
                        [10, 100, 80, 120],
                        [10, 10, 80, 30],
                        [100, 10, 180, 30],
                    ],
                }
            }
        ]

        result = parse_predictions(predictions, min_confidence=0.5)

        self.assertEqual([line.text for line in result.lines], ["위", "낮은 신뢰도", "아래"])
        self.assertEqual(result.raw_text, "위\n낮은 신뢰도\n아래")
        self.assertEqual(result.text, "위\n아래")
        self.assertAlmostEqual(result.confidence, (0.8 + 0.2 + 0.9) / 3)
        self.assertEqual(result.lines[0].box, (10.0, 10.0, 80.0, 30.0))

    def test_pipeline_is_created_lazily_and_cached(self) -> None:
        service = _CountingPaddleService()

        self.assertIsNone(service._pipeline)
        first = service._get_pipeline()
        second = service._get_pipeline()

        self.assertIs(first, second)
        self.assertEqual(service.create_count, 1)

    def test_predict_calls_are_serialized_for_one_pipeline(self) -> None:
        pipeline = _ConcurrentProbePipeline()
        service = PaddleOcrService("cpu", "korean")
        service._pipeline = pipeline
        image = Image.new("RGB", (20, 20), "white")

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(service.extract_text, image) for _ in range(2)]
            for future in futures:
                future.result()

        self.assertEqual(pipeline.maximum_active_calls, 1)


class _CountingPaddleService(PaddleOcrService):
    def __init__(self) -> None:
        super().__init__("cpu", "korean")
        self.create_count = 0

    def _create_pipeline(self):
        self.create_count += 1
        return object()


class _ConcurrentProbePipeline:
    def __init__(self) -> None:
        self.active_calls = 0
        self.maximum_active_calls = 0
        self.lock = Lock()

    def predict(self, _image):
        with self.lock:
            self.active_calls += 1
            self.maximum_active_calls = max(
                self.maximum_active_calls,
                self.active_calls,
            )
        sleep(0.03)
        with self.lock:
            self.active_calls -= 1
        return []


if __name__ == "__main__":
    unittest.main()
