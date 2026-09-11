import unittest

from ai.consultation.risk_detector import detect_emergency


class DetectEmergencyTest(unittest.TestCase):
    def test_detects_known_high_risk_keyword(self) -> None:
        self.assertTrue(detect_emergency("갑자기 가슴 통증이 심해요"))
        self.assertTrue(detect_emergency("숨쉬기 힘들어요"))
        self.assertTrue(detect_emergency("손발이 마비된 것 같아요"))

    def test_detects_keyword_with_wider_word_gap(self) -> None:
        # 실제 라이브 테스트(2026-09)에서 놓친 사례 - "가슴"과 "쥐어짜" 사이에 부위
        # 수식어("한가운데가")가 끼어 갭이 7자가 되면서 기존 6자 허용치를 넘었었다.
        self.assertTrue(detect_emergency("가슴 한가운데가 쥐어짜듯이 아프고 식은땀이 나요"))

    def test_does_not_flag_ordinary_symptoms(self) -> None:
        self.assertFalse(detect_emergency("어제부터 콧물이 나요"))
        self.assertFalse(detect_emergency("무릎이 좀 아파요"))

    def test_still_catches_combined_case_that_motivated_removed_keyword(self) -> None:
        # "가슴 답답" 키워드가 원래 이 문장을 잡으려고 추가됐었다("가슴"-"통증" 사이
        # 7자가 당시 6자 갭 허용치를 넘어서 놓쳤음). 그 키워드를 제거한 뒤에도
        # gap=15로 넓힌 "가슴 통증" 키워드만으로 여전히 잡혀야 재현율 손실이 없다.
        self.assertTrue(detect_emergency("가슴이 답답하고 통증이 있어요"))

    def test_does_not_flag_common_stress_related_chest_tightness(self) -> None:
        # 회귀 테스트(2026-09) - "가슴 답답"을 응급 키워드에 넣었더니 스트레스·소화불량
        # 등 일상적인 비응급 표현까지 걸려서, 실제 상담 다수가 LLM 답변 대신 고정
        # 응급 문구만 받는 품질 저하가 실제로 보고됐다. 응급 신호 없이 "답답함"만
        # 있는 경우는 다시는 잡히면 안 된다.
        self.assertFalse(detect_emergency("요즘 스트레스를 받아서 그런지 가슴이 답답해요"))
        self.assertFalse(detect_emergency("체한 것 같은데 가슴이 답답하고 소화가 안돼요"))
        self.assertFalse(detect_emergency("밥을 급하게 먹었더니 가슴이 답답하네요"))

    def test_empty_text_is_not_emergency(self) -> None:
        self.assertFalse(detect_emergency(""))


if __name__ == "__main__":
    unittest.main()
