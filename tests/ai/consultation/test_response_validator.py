import unittest

from ai.consultation.response_validator import validate


class ValidateTest(unittest.TestCase):
    def test_leaves_safe_answer_unchanged(self) -> None:
        answer = "충분한 휴식과 수분 섭취가 도움이 될 수 있습니다."
        self.assertEqual(validate(answer), answer)

    def test_appends_warning_for_mg_dosage(self) -> None:
        answer = "타이레놀 500mg을 복용하세요."
        result = validate(answer)
        self.assertIn(answer, result)
        self.assertIn("[안전 안내]", result)

    def test_appends_warning_for_tablet_count(self) -> None:
        result = validate("하루 3정씩 드세요.")
        self.assertIn("[안전 안내]", result)

    def test_does_not_false_positive_on_unrelated_text(self) -> None:
        answer = "정확한 진단을 위해 의료진과 상담하는 것이 좋습니다."
        self.assertEqual(validate(answer), answer)

    def test_strips_trailing_repeated_short_tokens(self) -> None:
        # 일부 원격 모델이 정상 답변 뒤에 종료 토큰 처리를 잘못해서 같은 줄을
        # 반복하는 현상이 관찰됐다 — 답변 본문은 지키고 반복 꼬리만 잘라야 한다.
        good_answer = "충분한 휴식과 수분 섭취가 도움이 될 수 있습니다."
        noisy = good_answer + "\n" + "\n".join(["[]"] * 6)
        self.assertEqual(validate(noisy), good_answer)

    def test_strips_trailing_repeated_lines_with_blank_lines_between(self) -> None:
        good_answer = "가능하다면 내과에서 진료를 받아보시는 것을 추천드립니다."
        noisy = good_answer + "\n\ndisplay comment\n\n\n\ndisplay comment\n\ndisplay comment"
        self.assertEqual(validate(noisy), good_answer)

    def test_strips_trailing_repeated_two_line_pattern(self) -> None:
        # 실제로 관찰된 사례: "caution/indicator" 두 줄이 번갈아 반복.
        good_answer = "내과에서 진료를 받아보시는 것도 고려해볼 수 있습니다."
        noisy = good_answer + "\n" + "\n".join(
            ["caution: 이 정보는 일반적인 내용입니다.", "indicator: medical"] * 3
        )
        self.assertEqual(validate(noisy), good_answer)

    def test_does_not_strip_below_minimum_repeat_threshold(self) -> None:
        # 반복이 2번뿐이면(우연의 일치일 수 있음) 그대로 둔다 — 오탐으로 실제 내용을
        # 지우면 안 되기 때문.
        answer = "괜찮습니다.\n괜찮습니다."
        self.assertEqual(validate(answer), answer)

    def test_strips_special_tokens_even_when_not_repeated(self) -> None:
        good_answer = "내과에서 진료를 받아보시는 것도 고려해볼 수 있습니다."
        self.assertEqual(validate(good_answer + "</s></s>"), good_answer)

    def test_strips_self_generated_disclaimer_paragraph(self) -> None:
        # 실제 관찰된 사례 — 면책 문구는 프론트엔드 배너가 담당하는데, 모델이 자기
        # 나름의 면책 문구를 답변 끝에 또 붙였다.
        good_answer = "내과에서 진료를 받아보시는 것도 고려해볼 수 있습니다."
        noisy = (
            good_answer
            + "\n\n**면책 조항:** 저는 의료 전문가가 아니므로, 이 정보는 의료적인 조언으로 해석될 수 없습니다."
        )
        self.assertEqual(validate(noisy), good_answer)

    def test_does_not_strip_paragraph_without_disclaimer_signal(self) -> None:
        answer = "충분한 휴식을 취하세요.\n\n증상이 지속되면 병원을 방문하세요."
        self.assertEqual(validate(answer), answer)


if __name__ == "__main__":
    unittest.main()
