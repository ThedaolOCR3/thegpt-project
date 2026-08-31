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

# 토크나이저 종료/시작 특수 토큰이 디코딩 과정에서 그대로 텍스트에 섞여 나오는 경우가
# 있었다("...</s></s>") — 사용자에게 보일 이유가 전혀 없는 내부 토큰이라 몇 번 나오든
# 무조건 제거한다(반복 횟수 조건 없음).
_SPECIAL_TOKEN_PATTERN = re.compile(r"</?s>")

# 프롬프트에서 "면책 문구는 백엔드가 자동으로 붙이니 직접 쓰지 말라"고 지시해도, 일부
# 모델이 자기 나름의 면책 문구를 답변 끝에 덧붙이는 경우가 관찰됐다("**면책 조항:**
# 저는 의료 전문가가 아니므로...") — 실제 면책 문구는 프론트엔드 배너가 담당하므로
# 이런 자체 생성 문단은 중복이자 잡음이다. 마지막 문단이 이런 신호를 담고 있으면 제거한다.
_SELF_DISCLAIMER_SIGNALS = (
    "면책 조항",
    "면책조항",
    "disclaimer",
    "의료 전문가가 아니",
    "전문가가 아니므로",
    "전문적인 의학적 조언을 대체",
    "의학적 조언으로 간주",
    "의학적 조언으로 해석",
)


def _strip_special_tokens(text: str) -> str:
    return _SPECIAL_TOKEN_PATTERN.sub("", text)


def _strip_self_generated_disclaimer(text: str) -> str:
    paragraphs = text.split("\n\n")
    if len(paragraphs) < 2:
        return text
    last = paragraphs[-1].strip().lower()
    if last and any(signal in last for signal in _SELF_DISCLAIMER_SIGNALS):
        return "\n\n".join(paragraphs[:-1]).rstrip()
    return text

# 일부 원격 모델이 정상 답변을 다 낸 뒤에도 멈추지 않고 같은 줄이나 몇 줄짜리 패턴
# ("[]" 반복, "caution: .../indicator: ..." 번갈아 반복 등)을 max_tokens까지 채우는
# 경우가 관찰됐다 — 매번 반복되는 내용이 달라서 특정 문자열 하나만 정규식으로 잡을 수
# 없다. 대신 "1~4줄짜리 어떤 패턴이 끝에서부터 연속으로 여러 번 반복되는지"만 일반적으로
# 검사한다 — 프롬프트 내용과 무관한 모델/서버 쪽 종료 토큰 처리 문제로 보이며, 반복이
# 시작되기 전까지의 정상 답변은 그대로 둔다.
_MIN_TRAILING_REPEATS = 3
_MAX_REPEAT_UNIT_LINES = 4


def _strip_trailing_repeated_lines(text: str) -> str:
    lines = text.split("\n")
    non_blank = [(i, line.strip().lower()) for i, line in enumerate(lines) if line.strip()]
    if not non_blank:
        return text

    indices = [i for i, _ in non_blank]
    normalized = [content for _, content in non_blank]
    total = len(normalized)

    best_cut: int | None = None
    for unit in range(1, _MAX_REPEAT_UNIT_LINES + 1):
        if total < unit * _MIN_TRAILING_REPEATS:
            continue
        pattern = normalized[total - unit :]
        repeats = 1
        pos = total - unit
        while pos - unit >= 0 and normalized[pos - unit : pos] == pattern:
            repeats += 1
            pos -= unit
        if repeats >= _MIN_TRAILING_REPEATS:
            cut_line_index = indices[pos]
            if best_cut is None or cut_line_index < best_cut:
                best_cut = cut_line_index

    if best_cut is None:
        return text
    return "\n".join(lines[:best_cut]).rstrip()


def _contains_risky_dosage(text: str) -> bool:
    return any(pattern.search(text) for pattern in _RISKY_DOSAGE_PATTERNS)


def validate(answer: str) -> str:
    """위험한 패턴이 없으면 원문 그대로 반환한다. 면책 문구는 여기서 붙이지 않는다
    (그건 pipeline.py의 책임 — 이 함수는 LLM 원문 자체만 검증한다)."""
    answer = _strip_special_tokens(answer)
    answer = _strip_self_generated_disclaimer(answer)
    answer = _strip_trailing_repeated_lines(answer)
    if _contains_risky_dosage(answer):
        return answer + _DOSAGE_WARNING
    return answer
