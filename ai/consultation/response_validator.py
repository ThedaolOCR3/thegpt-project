"""LLM 응답이 나간 뒤, 시스템 프롬프트가 놓쳤을 수도 있는 위험한 표현을 잡아내는
마지막 안전망. 프롬프트로만 막고 있던 것에 대한 이중 안전장치.

지금은 구체적인 약물 용량/처방 패턴만 정규식으로 잡는다 — 확정적 진단 표현("~입니다")
자체를 자동으로 순화하는 건 정교한 NLP나 LLM 재작성이 필요해서 범위 밖으로 뒀다
(TODO, ai/consultation/CLAUDE.md 참고).
"""
import re

_RISKY_DOSAGE_PATTERNS = (
    re.compile(r"\d+\s?mg"),
    re.compile(r"\d+\s?ml", re.IGNORECASE),
    # "3정" 같은 처방 단위. "2정도"/"3정확히"처럼 흔히 뒤따라오는 단어만 골라 제외한다
    # (뒤에 한글이 오면 무조건 제외하면 "3정씩"/"3정을" 같은 정상 케이스까지 놓친다).
    re.compile(r"\d+\s?정(?!도|확|말|보|신|리|지|상)"),
)

_DOSAGE_WARNING = "\n\n[안전 안내] 구체적인 약물 용량/처방은 반드시 의사·약사와 상담 후 결정하세요."


def _contains_risky_dosage(text: str) -> bool:
    return any(pattern.search(text) for pattern in _RISKY_DOSAGE_PATTERNS)


def validate(answer: str) -> str:
    """위험한 패턴이 없으면 원문 그대로 반환한다. 면책 문구는 여기서 붙이지 않는다
    (그건 pipeline.py의 책임 — 이 함수는 LLM 원문 자체만 검증한다)."""
    if _contains_risky_dosage(answer):
        return answer + _DOSAGE_WARNING
    return answer
