"""system_prompt.md + [진료과 분류 결과] + [참고 의료 정보] + [사용자 질문]을
`ai.llm`이 바로 받을 수 있는 `LlmMessage` 튜플로 조립한다.

여기서 조립을 끝내고 나면 그 뒤(LLM 호출, 응답에 면책 문구 붙이기)는 이 파일의
책임이 아니다 — pipeline.py 참고.
"""
from functools import lru_cache
from pathlib import Path

from ai.llm.contracts import LlmMessage

from .classifier import DepartmentResult

_SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"


@lru_cache(maxsize=1)
def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _department_block(result: DepartmentResult | None) -> str | None:
    """진료과 참고정보를 "[진료과 분류 결과]" 같은 대괄호 라벨 블록이 아니라 괄호로 감싼
    지시문 형태로 만든다 — 소형 모델이 대괄호 라벨을 데이터 헤더로 착각해서 답변에
    그대로 되풀이하는 문제가 있었다(라벨을 없애니 재현되지 않음)."""
    if result is None or result.department is None:
        return None
    return (
        f"(참고용 진료과 정보 — {result.department} 관련 가능성, 신뢰도 {result.confidence}. "
        "이 정보는 답변 마지막에 자연스러운 문장으로 한 번만 녹여서 언급하고, "
        "이 괄호 안 문장 자체는 절대 답변에 옮기지 마세요.)"
    )


def build_messages(
    user_question: str,
    *,
    department_result: DepartmentResult | None = None,
    reference_info_block: str | None = None,
) -> tuple[LlmMessage, ...]:
    """system_prompt.md가 그대로 system 메시지가 되고, 나머지 입력 정보 3종은
    프롬프트의 "# 2. 입력 정보" 형식 그대로 하나의 user 메시지에 담긴다."""
    sections: list[str] = []

    department_block = _department_block(department_result)
    if department_block:
        sections.append(department_block)

    if reference_info_block:
        sections.append(reference_info_block)

    sections.append(f"[사용자 질문]\n{user_question.strip()}")

    return (
        LlmMessage(role="system", content=_load_system_prompt()),
        LlmMessage(role="user", content="\n\n".join(sections)),
    )
