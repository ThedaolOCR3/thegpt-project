import unittest

from ai.consultation.risk_detector import detect_emergency


class DetectEmergencyTest(unittest.TestCase):
    def test_detects_known_high_risk_keyword(self) -> None:
        self.assertTrue(detect_emergency("갑자기 가슴 통증이 심해요"))
        self.assertTrue(detect_emergency("숨쉬기 힘들어요"))
        self.assertTrue(detect_emergency("손발이 마비된 것 같아요"))

    def test_does_not_flag_ordinary_symptoms(self) -> None:
        self.assertFalse(detect_emergency("어제부터 콧물이 나요"))
        self.assertFalse(detect_emergency("무릎이 좀 아파요"))

    def test_empty_text_is_not_emergency(self) -> None:
        self.assertFalse(detect_emergency(""))


if __name__ == "__main__":
    unittest.main()
