"""6개 어댑터의 to_normalized() 테스트. 실제 HuggingFace 네트워크 호출은 하지 않고,
STEP 0에서 확인한 실제 데이터셋 필드 구조를 그대로 본뜬 fixture row만 사용한다.
"""
import unittest

from ai.rag.ingestion.adapters.ai_healthcare_qa import AiHealthcareQaAdapter
from ai.rag.ingestion.adapters.asan import AsanHealthInfoAdapter
from ai.rag.ingestion.adapters.genmed_gpt import GenMedGptAdapter
from ai.rag.ingestion.adapters.health_search_qa import HealthSearchQaAdapter
from ai.rag.ingestion.adapters.komed_instruct import KoMedInstructAdapter
from ai.rag.ingestion.adapters.snuh_clinical_qa import SnuhClinicalQaAdapter


class AsanHealthInfoAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = AsanHealthInfoAdapter()

    def test_combines_instruction_and_output(self) -> None:
        row = {
            "instruction": "경피적 간담도조영술의 정의에 대해서 설명해주세요.",
            "input": "",
            "output": "경피적 간담도조영술은 담도에 조영제를 직접 투여한 후 X-선 촬영을 하는 검사입니다.",
        }
        record = self.adapter.to_normalized(row, 0)
        self.assertIsNotNone(record)
        self.assertIn("경피적 간담도조영술의 정의", record.content)
        self.assertIn("조영제를 직접 투여", record.content)
        self.assertEqual(record.original_id, "0")
        self.assertEqual(record.original_dataset, "ChuGyouk/Asan-AMC-Healthinfo")

    def test_empty_output_is_skipped(self) -> None:
        row = {"instruction": "질문", "input": "", "output": ""}
        self.assertIsNone(self.adapter.to_normalized(row, 0))


class SnuhClinicalQaAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = SnuhClinicalQaAdapter()
        self.row = {
            "question_id": "1",
            "chief_complaint": "가려움증",
            "purpose": "가려움증 감별",
            "question": "62세 남자 환자가 전신 가려움증을 주소로 내원하였다.",
            "exam": "AST 85U/L, ALP 420U/L",
            "options": "{'option_A': '당뇨병', 'option_B': '약물 부작용'}",
            "answer": "C",
            "explanation": "담즙정체성 간기능 이상 소견은 원발성 담즙성 담관염을 시사합니다.",
            "source": "출처: Harrison's Principles of Internal Medicine",
            "category": "Gastroenterology",
        }

    def test_content_excludes_raw_options(self) -> None:
        record = self.adapter.to_normalized(self.row, 0)
        self.assertIsNotNone(record)
        self.assertNotIn("option_A", record.content)
        self.assertNotIn("당뇨병", record.content)

    def test_content_includes_question_exam_explanation(self) -> None:
        record = self.adapter.to_normalized(self.row, 0)
        self.assertIn("전신 가려움증", record.content)
        self.assertIn("AST 85U/L", record.content)
        self.assertIn("원발성 담즙성 담관염", record.content)

    def test_content_excludes_trailing_mcq_prompt_sentence(self) -> None:
        # 실제 관찰된 사례 - question 필드 끝에 "다음 중 ... 은?" 객관식 시험 문제
        # 형식의 문장이 붙어서 온다. 이건 의료 지식이 아니라 문항 형식이라 제외한다.
        row = dict(self.row)
        row["question"] = (
            "62세 남자 환자가 전신 가려움증을 주소로 내원하였다. 비장이 촉지된다. "
            "다음 중 이 환자의 가려움증의 원인으로 가장 가능성이 높은 질환은?"
        )
        record = self.adapter.to_normalized(row, 0)
        self.assertIn("전신 가려움증", record.content)
        self.assertIn("비장이 촉지된다", record.content)
        self.assertNotIn("다음 중", record.content)
        # question 필드 원본 자체는 안 건드린다(참고용으로 그대로 보존).
        self.assertIn("다음 중", record.question)

    def test_strips_mcq_prompt_without_dayeum_jung_prefix(self) -> None:
        # "다음 중"으로 시작하지 않는 마무리 질문도(예: "...가장 가능성이 높은
        # 진단은?") 실제 데이터에서 관찰됐다.
        row = dict(self.row)
        row["question"] = (
            "62세 남자 환자가 3개월 전부터 시작된 전신 가려움증을 주소로 내원하였다. "
            "이 환자의 진단으로 가장 가능성이 높은 것은?"
        )
        record = self.adapter.to_normalized(row, 0)
        self.assertIn("전신 가려움증", record.content)
        self.assertNotIn("가장 가능성이 높은 것은", record.content)

    def test_question_that_is_entirely_mcq_prompt_keeps_original(self) -> None:
        # 전부 시험 문제 형식이라 지울 문장만 남으면(빈 content가 되면 안 되므로)
        # 원본 question을 그대로 쓴다.
        row = dict(self.row)
        row["question"] = "다음 중 가장 가능성이 높은 진단은?"
        record = self.adapter.to_normalized(row, 0)
        self.assertIn("다음 중 가장 가능성이 높은 진단은?", record.content)

    def test_uses_question_id_over_index(self) -> None:
        record = self.adapter.to_normalized(self.row, 5)
        self.assertEqual(record.original_id, "1")

    def test_known_english_category_maps_to_korean_department(self) -> None:
        record = self.adapter.to_normalized(self.row, 0)
        self.assertEqual(record.department, ["소화기내과"])
        self.assertTrue(record.metadata.get("generated_metadata"))

    def test_unknown_category_leaves_department_empty_not_guessed(self) -> None:
        row = dict(self.row, category="SomeUnknownSpecialty")
        record = self.adapter.to_normalized(row, 0)
        self.assertEqual(record.department, [])


class HealthSearchQaAdapterTest(unittest.TestCase):
    def test_uses_korean_fields_not_english_original(self) -> None:
        row = {
            "id": "1",
            "question": "Are benign brain tumors serious?",
            "question_ko": "양성 뇌종양은 심각한가요?",
            "answer_ko": "양성 뇌종양은 일반적으로 악성 뇌종양보다 덜 위험한 것으로 간주됩니다.",
        }
        record = HealthSearchQaAdapter().to_normalized(row, 0)
        self.assertIn("양성 뇌종양은 심각한가요", record.content)
        self.assertIn("악성 뇌종양보다 덜 위험", record.content)
        self.assertEqual(record.metadata.get("question_en"), "Are benign brain tumors serious?")

    def test_missing_korean_translation_is_skipped(self) -> None:
        row = {"id": "1", "question": "x", "question_ko": "", "answer_ko": ""}
        self.assertIsNone(HealthSearchQaAdapter().to_normalized(row, 0))


class KoMedInstructAdapterTest(unittest.TestCase):
    def test_noinput_marker_is_not_treated_as_real_content(self) -> None:
        row = {
            "idx": "0",
            "instruction": "폐의 종괴가 호흡 곤란을 유발할 수 있는 이유를 설명하세요.",
            "input": "<noinput>",
            "output": "종괴가 물리적으로 공기 통로를 막아 호흡 곤란을 유발할 수 있습니다.",
        }
        record = KoMedInstructAdapter().to_normalized(row, 0)
        self.assertNotIn("<noinput>", record.content)
        self.assertEqual(record.original_id, "0")

    def test_real_input_is_included(self) -> None:
        row = {
            "idx": "1",
            "instruction": "질문",
            "input": "실제 추가 맥락 정보입니다.",
            "output": "답변 내용입니다.",
        }
        record = KoMedInstructAdapter().to_normalized(row, 0)
        self.assertIn("실제 추가 맥락 정보", record.content)

    def test_strips_trailing_answer_restatement(self) -> None:
        # 실제 관찰된 사례(500행 표본 중 45.7%) - 설명을 다 쓴 뒤 "정답은: ..."으로
        # 같은 내용을 중복 요약해서 덧붙인다. 새 정보가 없으므로 제거한다.
        row = {
            "idx": "2",
            "instruction": "폐 종괴가 호흡곤란을 유발하는 이유는?",
            "input": "<noinput>",
            "output": (
                "폐에 덩어리가 생기면 공기 통로를 막아 호흡곤란이 발생할 수 있습니다. "
                "염증과 손상을 일으켜 폐 기능을 감소시킬 수도 있습니다.\n\n"
                "정답은: 폐의 덩어리는 공기 통로를 막고 염증을 유발하여 호흡 곤란을 일으킵니다."
            ),
        }
        record = KoMedInstructAdapter().to_normalized(row, 0)
        self.assertIsNotNone(record)
        self.assertIn("공기 통로를 막아 호흡곤란이 발생", record.content)
        self.assertNotIn("정답은", record.content)

    def test_output_that_is_entirely_answer_restatement_keeps_original(self) -> None:
        row = {
            "idx": "3",
            "instruction": "질문",
            "input": "<noinput>",
            "output": "정답은: 짧은 답변입니다.",
        }
        record = KoMedInstructAdapter().to_normalized(row, 0)
        self.assertIsNotNone(record)
        self.assertIn("정답은", record.content)

    def test_ai_self_referential_refusal_is_excluded(self) -> None:
        # 실제 관찰된 사례(500행 중 0.8%) - "당신의 기분을 설명하세요" 같은 AI에게
        # 불가능한 instruction에 대해 모델이 거절 응답만 냄 - 의료 지식이 없다.
        row = {
            "idx": "4",
            "instruction": "새로운 항생제 복용을 시작한 후 기분이 어떤지 설명하세요.",
            "input": "<noinput>",
            "output": (
                "인공지능인 저는 신체 감각이나 감정을 경험할 수 없기 때문에 "
                "새로운 항생제 복용 후 기분이 어떤지 설명할 수 없습니다."
            ),
        }
        record = KoMedInstructAdapter().to_normalized(row, 0)
        self.assertIsNone(record)

    def test_output_that_is_near_copy_of_input_is_excluded(self) -> None:
        # 카드가 경고하는 "output에 input 내용이 그대로 들어가는 경우"를 재현.
        source_text = (
            "겸상 적혈구 질환은 HBB 유전자의 돌연변이로 인해 발생합니다. "
            "이 돌연변이는 잘못된 형태의 적혈구를 만들어 혈류를 차단하여 통증 위기를 초래할 수 있습니다."
        )
        row = {
            "idx": "5",
            "instruction": "이 문장을 쉽게 설명하세요.",
            "input": source_text,
            "output": source_text,  # 사실상 그대로 복사
        }
        record = KoMedInstructAdapter().to_normalized(row, 0)
        self.assertIsNone(record)

    def test_genuinely_rewritten_output_is_not_flagged_as_leakage(self) -> None:
        # 실제 관찰된 정상 사례 - 원문을 진짜로 쉬운 말로 바꿔 쓴 경우는 통과해야 한다.
        row = {
            "idx": "6",
            "instruction": "이러한 유전학 전문 용어를 더 쉬운 용어로 번역하세요.",
            "input": (
                "겸상 적혈구 질환은 HBB 유전자의 돌연변이로 인해 발생합니다. 이 돌연변이는 "
                "잘못된 형태의 적혈구를 만들어 혈류를 차단하여 통증 위기를 초래할 수 있습니다."
            ),
            "output": (
                "겸상 적혈구 질환은 HBB 유전자의 변화로 인해 발생하는 질환입니다. 이러한 변화로 "
                "인해 적혈구의 모양이 비정상적으로 변하여 혈액의 흐름을 차단하고 위기라고 하는 "
                "고통스러운 에피소드를 유발할 수 있습니다."
            ),
        }
        record = KoMedInstructAdapter().to_normalized(row, 0)
        self.assertIsNotNone(record)


class GenMedGptAdapterTest(unittest.TestCase):
    def test_fixed_instruction_prompt_template_is_excluded(self) -> None:
        row = {
            "instruction": "당신이 의사라면 환자의 설명을 바탕으로 의학적 질문에 답변해 주세요.",
            "input": "저는 갑작스럽고 빈번한 공황 발작을 경험하고 있습니다.",
            "output": "공황 장애를 앓고 계신 것 같습니다. 심리 치료부터 시작하는 것을 권장합니다.",
        }
        record = GenMedGptAdapter().to_normalized(row, 0)
        self.assertIsNotNone(record)
        self.assertNotIn("당신이 의사라면", record.content)
        self.assertIn("공황 발작", record.content)
        self.assertIn("심리 치료", record.content)


class AiHealthcareQaAdapterTest(unittest.TestCase):
    def test_gated_adapter_raises_permission_error(self) -> None:
        adapter = AiHealthcareQaAdapter()
        with self.assertRaises(PermissionError):
            adapter.to_normalized({}, 0)
        with self.assertRaises(PermissionError):
            list(adapter.load_raw())

    def test_gated_adapter_accepts_shuffle_seed_without_type_error(self) -> None:
        # run_ingestion_pipeline은 모든 어댑터에 shuffle_seed=를 넘긴다 - gated
        # 어댑터가 이 kwarg를 안 받으면 의도한 PermissionError 대신 TypeError가
        # 나서 "왜 실패했는지"가 헷갈리게 된다.
        adapter = AiHealthcareQaAdapter()
        with self.assertRaises(PermissionError):
            list(adapter.load_raw(20, shuffle_seed=42))


if __name__ == "__main__":
    unittest.main()
