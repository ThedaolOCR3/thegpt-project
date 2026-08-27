"""검색된 청크 → 시스템 프롬프트의 `[참고 의료 정보]` 블록 텍스트로 변환한다.

이 파일은 `ai.rag`의 `RetrievedChunk` 타입을 직접 import하지 않는다 — 지금 RAG
쪽(Jina v4 + BGE-M3, DB 저장/검색)이 아직 정리 중이라 강하게 결합하면 그쪽이 바뀔
때마다 여기도 깨진다. 대신 `.text`(또는 `.content`)와 선택적으로 `.source` 속성만
있으면 되는 duck typing으로 받는다 — `ai.rag.RetrievedChunk`든 다른 무엇이든 그대로
넘기면 된다.

절대 규칙(루트 CLAUDE.md, ai/rag/CLAUDE.md에서 이어짐): 여기 들어오지 않은 텍스트를
"참고 의료 정보"인 것처럼 만들어내면 안 된다 — 이 함수가 실제로 받은 chunk 이외의
내용은 이 블록에 절대 추가하지 않는다.
"""
from typing import Any, Protocol

# 프롬프트에 실어 보내는 참고 정보 총량 상한 — 토큰 낭비/컨텍스트 과다 방지.
DEFAULT_MAX_CHUNKS = 5
DEFAULT_MAX_CHARS_PER_CHUNK = 800


class _RetrievedLike(Protocol):
    text: str


def _chunk_text(chunk: Any) -> str:
    text = getattr(chunk, "text", None) or getattr(chunk, "content", None) or ""
    return str(text).strip()


def _chunk_source(chunk: Any) -> str | None:
    source = getattr(chunk, "source", None)
    return str(source).strip() if source else None


def build_reference_info_block(
    chunks: list[Any] | None,
    *,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    max_chars_per_chunk: int = DEFAULT_MAX_CHARS_PER_CHUNK,
) -> str | None:
    """[참고 의료 정보] 블록 문자열을 만든다. 검색 결과가 없으면 None을 반환하고,
    호출하는 쪽(prompt_builder)이 "# 5. 참고 의료 정보가 없는 경우" 경로를 타게 한다."""
    if not chunks:
        return None

    lines = ["[참고 의료 정보]"]
    used = 0
    for chunk in chunks:
        text = _chunk_text(chunk)
        if not text:
            continue
        if len(text) > max_chars_per_chunk:
            text = text[:max_chars_per_chunk].rstrip() + "…"

        source = _chunk_source(chunk)
        used += 1
        lines.append(f"\n[문서 {used}]")
        if source:
            lines.append(f"출처: {source}")
        lines.append(text)

        if used >= max_chunks:
            break

    if used == 0:
        return None
    return "\n".join(lines)
