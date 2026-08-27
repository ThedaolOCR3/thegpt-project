import unittest

from ai.consultation.classifier import KeywordDepartmentClassifier


class KeywordDepartmentClassifierTest(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = KeywordDepartmentClassifier()

    def test_clear_single_match_returns_high_confidence(self) -> None:
        result = self.classifier.classify("얼굴에 발진이랑 두드러기가 났어요")
        self.assertEqual(result.department, "피부과")
        self.assertEqual(result.confidence, "높음")

    def test_ambiguous_match_returns_medium_confidence(self) -> None:
        # "두통" 하나만 있으면 신경과/내과 둘 다 후보라 확정하지 않는다.
        result = self.classifier.classify("두통이 있어요")
        self.assertIsNotNone(result.department)
        self.assertIn(result.confidence, ("중간", "높음"))

    def test_no_match_returns_low_confidence_and_no_department(self) -> None:
        result = self.classifier.classify("안녕하세요")
        self.assertIsNone(result.department)
        self.assertEqual(result.confidence, "낮음")

    def test_empty_query_returns_low_confidence(self) -> None:
        result = self.classifier.classify("   ")
        self.assertIsNone(result.department)
        self.assertEqual(result.confidence, "낮음")


if __name__ == "__main__":
    unittest.main()
