"""텍스트 청킹 — 문장 경계를 유지하며 '토큰' 예산 단위로 자르고, 청크 사이를 겹친다(overlap).

글자 수 대신 토큰 수를 쓰는 이유: 임베딩 모델이 실제로 소비하는 단위는 토큰이고,
한국어는 영어와 달리 글자 수 대비 토큰 수가 안정적이지 않아서(음절/서브워드 분리가
토크나이저마다 다름) 글자 수 기준 예산은 모델이 보는 것과 어긋난다. 임베딩 모델과
같은 토크나이저를 그대로 써서 예산을 맞춘다.

그 외 두 가지 안전장치:
- 문장 하나가 이미 예산을 넘으면(OCR로 뽑은 표/양식처럼 문장부호 없는 덩어리 텍스트)
  그 안에서 토큰 단위로 강제 분할한다 — 안 그러면 쪼개지지 않는 거대 청크가 생긴다.
- 공백뿐이거나 특수문자/기호만 있고 실제 내용(한글/영문/숫자)이 거의 없는 청크는
  버린다 — OCR 오탐지로 생기는 쓰레기 청크가 임베딩/검색 인덱스에 들어가지 않게.
"""
import re
from dataclasses import dataclass
from functools import lru_cache

_SENTENCE_END = re.compile(r"(?<=[.!?。！？])\s+")
# 한글 음절, 영문, 숫자가 하나도 없으면 "의미 있는 내용"이 아니라고 본다.
_MEANINGFUL_CONTENT = re.compile(r"[가-힣a-zA-Z0-9]")

DEFAULT_MAX_TOKENS = 300
DEFAULT_OVERLAP_TOKENS = 60
MIN_MEANINGFUL_CHARS = 2


@dataclass
class Chunk:
    index: int
    text: str


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


@lru_cache(maxsize=1)
def _get_tokenizer():
    from transformers import AutoTokenizer

    from .embedding import EMBEDDING_MODEL_NAME

    return AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME)


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_get_tokenizer().encode(text, add_special_tokens=False))


def is_garbage(text: str) -> bool:
    """공백뿐이거나, 기호/특수문자만 있고 실제 내용이 거의 없는 청크인지 판단."""
    stripped = text.strip()
    if not stripped:
        return True
    return len(_MEANINGFUL_CONTENT.findall(stripped)) < MIN_MEANINGFUL_CHARS


def _tail_by_tokens(text: str, n_tokens: int) -> str:
    tokenizer = _get_tokenizer()
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) <= n_tokens:
        return text
    return tokenizer.decode(ids[-n_tokens:])


def _force_split_by_tokens(text: str, max_tokens: int) -> list[str]:
    """문장부호가 없어 한 덩어리로 묶인 텍스트를 토큰 단위로 강제 분할한다."""
    tokenizer = _get_tokenizer()
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) <= max_tokens:
        return [text]
    return [tokenizer.decode(ids[i : i + max_tokens]) for i in range(0, len(ids), max_tokens)]


def chunk_text(
    text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[Chunk]:
    # 문장 단위로 거를 때 걸러야 쓰레기 문장이 다른 진짜 문장 사이에 낀 채로 청크에
    # 섞여 들어가는 걸 막는다 — 청크 전체를 보고 거르면 "쓰레기+진짜 내용"이 섞인
    # 청크는 안 걸러진다 (진짜 내용이 있으니 통째로는 "쓰레기"가 아니라서).
    sentences = [s for s in split_sentences(text) if not is_garbage(s)]
    raw_chunks: list[str] = []
    current = ""
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)

        if sentence_tokens > max_tokens:
            if current:
                raw_chunks.append(current)
                current, current_tokens = "", 0
            raw_chunks.extend(_force_split_by_tokens(sentence, max_tokens))
            continue

        if current and current_tokens + sentence_tokens > max_tokens:
            raw_chunks.append(current)
            # 다음 청크 앞부분에 이전 청크 끝부분을 겹쳐서 문맥이 뚝 끊기지 않게 한다.
            # decode/재encode 과정에서 토큰 수가 조금 흔들릴 수 있어(BPE 경계 문제),
            # overlap을 붙인 결과가 실제로 예산을 넘으면 이번만 overlap 없이 새로 시작한다
            # — 안 그러면 청크가 예산을 계속 넘는 채로 다음 문장까지 누적된다.
            overlap_text = _tail_by_tokens(current, overlap_tokens)
            candidate = f"{overlap_text} {sentence}".strip()
            candidate_tokens = count_tokens(candidate)
            if candidate_tokens <= max_tokens:
                current, current_tokens = candidate, candidate_tokens
            else:
                current, current_tokens = sentence, sentence_tokens
        else:
            current = f"{current} {sentence}".strip()
            current_tokens += sentence_tokens

    if current:
        raw_chunks.append(current)

    meaningful = [c.strip() for c in raw_chunks if not is_garbage(c)]
    return [Chunk(index=i, text=c) for i, c in enumerate(meaningful)]
