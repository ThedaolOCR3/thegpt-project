"""ChuGyouk/GenMedGPT-5k-ko 어댑터.

실제 필드(STEP 0 확인 결과): instruction, output, input.
언뜻 Alpaca 스타일 같지만 다른 어댑터들과 성격이 다르다 - instruction이 매 행
"당신이 의사라면 환자의 설명을 바탕으로 의학적 질문에 답변해 주세요." 같은 고정
역할 지시문(prompt template)이고, 실제 환자 증상/질문은 input에, 의사의 답변은
output에 들어있다. instruction은 dataset-specific prompt template 그 자체라서
명세가 명시적으로 제거하라는 대상 - content에 넣지 않는다.
"""
from typing import Any

from ..schema import NormalizedRecord
from .base import DatasetAdapter

SOURCE = "GenMedGPT-5k-ko"
SOURCE_TYPE = "doctor_patient_dialogue"


class GenMedGptAdapter(DatasetAdapter):
    source = SOURCE
    source_type = SOURCE_TYPE
    hf_path = "ChuGyouk/GenMedGPT-5k-ko"

    def to_normalized(self, raw_row: dict[str, Any], index: int) -> NormalizedRecord | None:
        patient_input = str(raw_row.get("input") or "").strip()
        output = str(raw_row.get("output") or "").strip()
        if not patient_input or not output:
            return None

        content = f"{patient_input}\n\n{output}"

        return NormalizedRecord(
            source=SOURCE,
            source_type=SOURCE_TYPE,
            content=content,
            original_id=str(index),
            original_dataset=self.hf_path,
            question=patient_input,
            answer=output,
            # 실제 HF dataset card 확인 결과 - ChatDoctor(GPT 생성 합성 대화)를
            # DeepL로 번역한 것. 원본도 생성 데이터고 전문가 검수 언급 없음 - 팀
            # 지시서 5-1절 "낮음" 기준.
            metadata={
                "language": "ko",
                "content_type": "doctor_patient_dialogue",
                "reliability": "ai_generated_unverified",
                "reliability_tier": "낮음",
                "reliability_reason": "ChatDoctor(GPT 생성 합성 대화) 원본을 DeepL로 번역, 전문가 검수 언급 없음",
                "source_tier": 3,
                "verification_status": "llm_generated_unverified",
            },
        )
