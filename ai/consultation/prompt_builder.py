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
    if result is None or result.department is None:
        return None
    return f"[진료과 분류 결과]\n추천 진료과: {result.department}\n신뢰도: {result.confidence}"


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
