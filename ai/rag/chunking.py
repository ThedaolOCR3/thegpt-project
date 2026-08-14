"""텍스트 청킹 — 문장 경계를 최대한 지키며 일정 길이로 자르고, 문맥이 끊기지 않게
청크 사이를 조금씩 겹친다(overlap)."""
import re
from dataclasses import dataclass

_SENTENCE_END = re.compile(r"(?<=[.!?。！？])\s+")


@dataclass
class Chunk:
    index: int
    text: str


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def chunk_text(text: str, max_chars: int = 400, overlap_chars: int = 80) -> list[Chunk]:
    sentences = split_sentences(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current)
            # 다음 청크 앞부분에 이전 청크 끝부분을 겹쳐서 문맥이 뚝 끊기지 않게 한다.
            current = (current[-overlap_chars:] + " " + sentence).strip()
        else:
            current = f"{current} {sentence}".strip()

    if current:
        chunks.append(current)

    return [Chunk(index=i, text=c) for i, c in enumerate(chunks) if c]
