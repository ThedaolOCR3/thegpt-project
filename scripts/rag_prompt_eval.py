"""기존 RAG 검색과 Remote MedGemma를 재사용하는 읽기 전용 프롬프트 평가 도구.

실행 흐름:
Prompt/질문 로드 -> Live 검색 또는 Snapshot 복원 -> 기존 Context Builder
-> 기존 LLM Application -> 로컬 TXT/JSONL/Snapshot 기록

이 스크립트는 평가 결과를 로컬 파일에만 기록한다. Live 모드의 DB 세션은
PostgreSQL에서 읽기 전용 트랜잭션으로 시작하며, 기존 검색 서비스만 호출한다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# 프롬프트 버전을 바꾸거나 파일 위치가 달라지면 이 영역만 수정한다.
PROMPT_V3_8_FILE = Path(
    r"G:\내 드라이브\02_프로젝트\3_메인프로젝트\06_FineTuning\00_common\prompts\medical_prompt_v3.8.json"
)
PROMPT_V4_1_FILE = Path(
    r"G:\내 드라이브\02_프로젝트\3_메인프로젝트\06_FineTuning\00_common\prompts\medical_prompt_v4.1_rag_prototype.json"
)
PROMPT_V4_2_FILE = Path(
    r"G:\내 드라이브\02_프로젝트\3_메인프로젝트\06_FineTuning\00_common\prompts\medical_prompt_v4.2_rag_evidence_guard.json"
)
PROMPT_V4_3_FILE = Path(
    r"G:\내 드라이브\02_프로젝트\3_메인프로젝트\06_FineTuning\00_common\prompts\medical_prompt_v4.3_rag_simplified.json"
)
DEFAULT_PROMPT_VERSION = "v4.1"
PROMPT_PRESETS: dict[str, dict[str, Path]] = {
    # V3.8 JSON에는 RAG template이 없으므로 V4.1의 입력 template만 함께 사용한다.
    "v3.8": {
        "prompt_file": PROMPT_V3_8_FILE,
        "rag_template_file": PROMPT_V4_1_FILE,
    },
    "v4.1": {
        "prompt_file": PROMPT_V4_1_FILE,
        "rag_template_file": PROMPT_V4_1_FILE,
    },
    "v4.2": {
        "prompt_file": PROMPT_V4_2_FILE,
        "rag_template_file": PROMPT_V4_1_FILE,
    },
    "v4.3": {
        "prompt_file": PROMPT_V4_3_FILE,
        "rag_template_file": PROMPT_V4_1_FILE,
    },
}

# 평가 대상을 바꿀 때 이 목록만 수정한다. 질문은 DB에 기록되지 않는다.
QUESTIONS = [
    {
        "id": "rag_01",
        "category": "consultation",
        "question": "식사 후 속이 쓰리고 신물이 올라옵니다. 어떤 원인이 있을 수 있나요?",
    },
    {
        "id": "rag_02",
        "category": "consultation",
        "question": "어제부터 기침과 가래가 심합니다. 어떻게 해야 하나요?",
    },
    {
        "id": "rag_03",
        "category": "ambiguous",
        "question": "요즘 손발이 가끔 저립니다. 어떤 원인 때문일 수 있나요?",
    },
    {
        "id": "rag_04",
        "category": "urgent",
        "question": "숨을 쉬기가 매우 힘들고 가슴이 답답합니다. 집에서 조금 기다려봐도 될까요?",
    },
    {
        "id": "rag_05",
        "category": "urgent",
        "question": "검은색 변을 봤고 어지럽고 식은땀이 납니다. 어떻게 해야 하나요?",
    },
]

MODEL_ID = "medgemma"
MAX_OUTPUT_TOKENS = 384
# MAX_OUTPUT_TOKENS = 256
TOP_K = 5
USE_RERANKER = False
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "rag_eval"
NO_REFERENCE_TEXT = "(검색된 참고 문서 없음)"
SNAPSHOT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PromptConfig:
    version: str
    system_prompt: str
    rag_context_template: str
    path: Path
    rag_template_path: Path


@dataclass(frozen=True)
class EvaluationQuestion:
    question_id: str
    category: str
    question: str


@dataclass(frozen=True)
class SnapshotChunk:
    """기존 Context Builder가 읽는 속성 형태로 Snapshot 청크를 복원한다."""

    index: int
    text: str
    score: float | None = None
    chunk_id: str | None = None
    document_id: str | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = None
    title: str | None = None
    url: str | None = None
    distance: float | None = None


@dataclass(frozen=True)
class SnapshotQuestion:
    question: EvaluationQuestion
    chunks: list[SnapshotChunk]
    retrieval_success: bool
    error_type: str | None = None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="기존 RAG와 Remote MedGemma를 이용한 읽기 전용 프롬프트 평가"
    )
    prompt_selection = parser.add_mutually_exclusive_group()
    prompt_selection.add_argument(
        "--prompt-version",
        choices=tuple(PROMPT_PRESETS),
        default=DEFAULT_PROMPT_VERSION,
        help=f"파일 상단 preset 선택 (기본: {DEFAULT_PROMPT_VERSION})",
    )
    prompt_selection.add_argument(
        "--prompt-file",
        type=Path,
        help="preset 대신 사용할 Prompt JSON (rag_context_template 포함 필요)",
    )
    parser.add_argument("--mode", choices=("live", "snapshot"), default="live")
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Snapshot 모드에서 재사용할 retrieval_snapshot.json",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--limit", type=int, help="앞에서부터 실행할 문항 수")
    selection.add_argument("--question-id", help="실행할 단일 질문 ID (예: rag_01)")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="timestamp 결과 폴더를 만들 상위 경로",
    )
    args = parser.parse_args(argv)

    if args.mode == "snapshot" and args.snapshot is None:
        parser.error("--mode snapshot에는 --snapshot이 필요합니다.")
    if args.mode == "live" and args.snapshot is not None:
        parser.error("--snapshot은 --mode snapshot에서만 사용할 수 있습니다.")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit은 1 이상이어야 합니다.")
    return args


def resolve_prompt_sources(args: argparse.Namespace) -> tuple[Path, Path | None]:
    """CLI 직접 경로 또는 파일 상단의 버전별 preset을 선택한다."""

    if args.prompt_file is not None:
        return args.prompt_file, None
    preset = PROMPT_PRESETS[args.prompt_version]
    return preset["prompt_file"], preset["rag_template_file"]


def load_prompt_config(
    path: Path,
    *,
    rag_template_path: Path | None = None,
) -> PromptConfig:
    resolved_path = path.expanduser().resolve()
    with resolved_path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("Prompt JSON 최상위 값은 객체여야 합니다.")

    required_values: dict[str, str] = {}
    for key in ("version", "system_prompt"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Prompt JSON의 {key!r} 값은 비어 있지 않은 문자열이어야 합니다."
            )
        required_values[key] = value.strip()

    template = payload.get("rag_context_template")
    resolved_template_path = resolved_path
    if not isinstance(template, str) or not template.strip():
        if rag_template_path is None:
            raise ValueError(
                "Prompt JSON에 rag_context_template이 없고 대체 template 파일도 지정되지 않았습니다."
            )
        resolved_template_path = rag_template_path.expanduser().resolve()
        with resolved_template_path.open(encoding="utf-8") as file:
            template_payload = json.load(file)
        if not isinstance(template_payload, dict):
            raise ValueError("RAG template JSON 최상위 값은 객체여야 합니다.")
        template = template_payload.get("rag_context_template")
        if not isinstance(template, str) or not template.strip():
            raise ValueError(
                "RAG template JSON의 'rag_context_template' 값이 필요합니다."
            )

    template = template.strip()
    for placeholder in ("{rag_context}", "{question}"):
        if placeholder not in template:
            raise ValueError(
                f"rag_context_template에 {placeholder} 자리표시자가 필요합니다."
            )

    return PromptConfig(
        version=required_values["version"],
        system_prompt=required_values["system_prompt"],
        rag_context_template=template,
        path=resolved_path,
        rag_template_path=resolved_template_path,
    )


def load_fixed_questions() -> list[EvaluationQuestion]:
    questions: list[EvaluationQuestion] = []
    seen_ids: set[str] = set()
    for row in QUESTIONS:
        question_id = str(row.get("id", "")).strip()
        category = str(row.get("category", "")).strip()
        question = str(row.get("question", "")).strip()
        if not question_id or not category or not question:
            raise ValueError(
                "QUESTIONS의 id/category/question은 비어 있을 수 없습니다."
            )
        if question_id in seen_ids:
            raise ValueError(f"중복된 질문 ID입니다: {question_id}")
        seen_ids.add(question_id)
        questions.append(EvaluationQuestion(question_id, category, question))
    return questions


def select_questions(
    questions: Sequence[EvaluationQuestion],
    *,
    limit: int | None,
    question_id: str | None,
) -> list[EvaluationQuestion]:
    if question_id:
        selected = [
            question for question in questions if question.question_id == question_id
        ]
        if not selected:
            raise ValueError(f"찾을 수 없는 질문 ID입니다: {question_id}")
        return selected
    return list(questions[:limit] if limit is not None else questions)


def load_snapshot(path: Path) -> tuple[dict[str, Any], list[SnapshotQuestion]]:
    resolved_path = path.expanduser().resolve()
    with resolved_path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict) or not isinstance(payload.get("questions"), list):
        raise ValueError("Snapshot에는 questions 배열이 필요합니다.")

    snapshot_questions: list[SnapshotQuestion] = []
    seen_ids: set[str] = set()
    for row in payload["questions"]:
        if not isinstance(row, dict):
            raise ValueError("Snapshot questions의 각 값은 객체여야 합니다.")
        question_id = _required_snapshot_string(row, "question_id")
        question_text = _required_snapshot_string(row, "question")
        category = _required_snapshot_string(row, "category")
        if question_id in seen_ids:
            raise ValueError(f"Snapshot에 중복된 질문 ID가 있습니다: {question_id}")
        seen_ids.add(question_id)

        contexts = row.get("retrieved_contexts")
        if not isinstance(contexts, list):
            raise ValueError(f"{question_id}: retrieved_contexts 배열이 필요합니다.")
        chunks = [
            _snapshot_chunk(item, position) for position, item in enumerate(contexts)
        ]
        retrieval_success = row.get("retrieval_success", True)
        if not isinstance(retrieval_success, bool):
            raise ValueError(
                f"{question_id}: retrieval_success는 boolean이어야 합니다."
            )
        error_type = row.get("error_type")
        snapshot_questions.append(
            SnapshotQuestion(
                question=EvaluationQuestion(question_id, category, question_text),
                chunks=chunks,
                retrieval_success=retrieval_success,
                error_type=str(error_type) if error_type else None,
            )
        )
    return payload, snapshot_questions


def _required_snapshot_string(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Snapshot의 {key!r} 값은 비어 있지 않은 문자열이어야 합니다.")
    return value.strip()


def _snapshot_chunk(item: Any, position: int) -> SnapshotChunk:
    if not isinstance(item, dict):
        raise ValueError("retrieved_contexts의 각 값은 객체여야 합니다.")
    content = item.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(
            "retrieved_contexts의 content는 비어 있지 않은 문자열이어야 합니다."
        )

    rank = item.get("rank", position + 1)
    if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
        raise ValueError("retrieved_contexts의 rank는 1 이상의 정수여야 합니다.")
    metadata = item.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("retrieved_contexts의 metadata는 객체 또는 null이어야 합니다.")

    return SnapshotChunk(
        index=rank - 1,
        text=content.strip(),
        score=_optional_number(item.get("score")),
        chunk_id=_optional_string(item.get("chunk_id")),
        document_id=_optional_string(item.get("document_id")),
        source=_optional_string(item.get("source")),
        metadata=metadata,
        title=_optional_string(item.get("title")),
        url=_optional_string(item.get("url")),
        distance=_optional_number(item.get("distance")),
    )


def _optional_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def create_output_directory(output_root: Path) -> Path:
    resolved_root = output_root.expanduser().resolve()
    resolved_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_dir = resolved_root / timestamp
    suffix = 1
    while output_dir.exists():
        output_dir = resolved_root / f"{timestamp}_{suffix:02d}"
        suffix += 1
    output_dir.mkdir()
    return output_dir


def prompt_version_slug(version: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", version).strip("._-")
    return slug or "unknown"


def compose_user_prompt(prompt: PromptConfig, chunks: list[Any], question: str) -> str:
    from ai.consultation.context import build_reference_info_block

    reference_block = build_reference_info_block(chunks, max_chunks=TOP_K)
    return prompt.rag_context_template.replace(
        "{rag_context}", reference_block or NO_REFERENCE_TEXT
    ).replace("{question}", question)


def serialize_chunks(chunks: Sequence[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for rank, chunk in enumerate(chunks, start=1):
        content = str(
            getattr(chunk, "text", None) or getattr(chunk, "content", "")
        ).strip()
        record: dict[str, Any] = {"rank": rank, "content": content}

        score = _optional_number(getattr(chunk, "score", None))
        if score is not None:
            record["score"] = score

        for attribute in ("chunk_id", "document_id", "source", "title", "url"):
            value = _optional_string(getattr(chunk, attribute, None))
            if value is not None:
                record[attribute] = value

        distance = _optional_number(getattr(chunk, "distance", None))
        if distance is not None:
            record["distance"] = distance

        metadata = getattr(chunk, "metadata", None)
        if isinstance(metadata, dict) and metadata:
            record["metadata"] = metadata
            for field in ("title", "url"):
                value = _optional_string(metadata.get(field))
                if value is not None and field not in record:
                    record[field] = value
        serialized.append(record)
    return serialized


def write_json(path: Path, payload: Any) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def append_result_text(
    path: Path,
    *,
    question: EvaluationQuestion,
    contexts: Sequence[dict[str, Any]],
    answer: str | None,
    prompt_version: str,
    retrieval_elapsed: float,
    llm_elapsed: float | None,
    total_elapsed: float,
    error_stage: str | None,
    error_type: str | None,
) -> None:
    lines = [
        "=" * 70,
        f"Question ID: {question.question_id}",
        f"Category: {question.category}",
        "Question:",
        question.question,
        "",
        "[Retrieval]",
    ]
    if contexts:
        for context in contexts:
            lines.extend(["", f"Top {context['rank']}"])
            for label, key in (
                ("Chunk ID", "chunk_id"),
                ("Document ID", "document_id"),
                ("Source", "source"),
                ("Title", "title"),
                ("URL", "url"),
                ("Score", "score"),
                ("Distance", "distance"),
            ):
                if key in context:
                    lines.append(f"{label}: {context[key]}")
            if "metadata" in context:
                lines.append(
                    "Metadata: "
                    + json.dumps(context["metadata"], ensure_ascii=False, default=str)
                )
            lines.extend(["Content:", str(context["content"])])
    else:
        lines.extend(["", NO_REFERENCE_TEXT])

    lines.extend(["", "[Final Answer]", answer or "(응답 생성 안 됨)"])
    if error_stage and error_type:
        lines.extend(["", "[Error]", f"Stage: {error_stage}", f"Type: {error_type}"])
    lines.extend(
        [
            "",
            "[Runtime]",
            f"Prompt Version: {prompt_version}",
            f"Retrieval Count: {len(contexts)}",
            f"Retrieval Elapsed: {retrieval_elapsed:.3f}s",
            f"LLM Elapsed: {llm_elapsed:.3f}s"
            if llm_elapsed is not None
            else "LLM Elapsed: N/A",
            f"Total Elapsed: {total_elapsed:.3f}s",
            "=" * 70,
            "",
        ]
    )
    with path.open("a", encoding="utf-8") as file:
        file.write("\n".join(lines))


def begin_read_only_postgres_transaction(db: Any) -> None:
    """Neon/PostgreSQL이 쓰기 시도를 거부하도록 검색 트랜잭션을 제한한다."""

    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy import text

        db.execute(text("SET TRANSACTION READ ONLY"))


def retrieve_live(question: str, providers: list[Any]) -> list[Any]:
    """질문별 독립 세션에서 기존 검색 서비스의 조회 경로만 실행한다."""

    from app.core.database import SessionLocal
    from app.services import rag_search_service

    db = SessionLocal()
    try:
        begin_read_only_postgres_transaction(db)
        return rag_search_service.search(
            db,
            question,
            top_k=TOP_K,
            use_reranker=USE_RERANKER,
            providers=providers,
        )
    finally:
        db.rollback()
        db.close()


async def generate_answer(prompt: PromptConfig, user_prompt: str) -> Any:
    from ai.llm.contracts import LlmMessage, ProviderGenerateRequest
    from app.services.llm_runtime import llm_application

    request = ProviderGenerateRequest(
        messages=(
            LlmMessage(role="system", content=prompt.system_prompt),
            LlmMessage(role="user", content=user_prompt),
        ),
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    return await llm_application.run(MODEL_ID, request)


def resolve_remote_model() -> Any:
    from app.services.llm_runtime import llm_application

    return llm_application.resolve_model(MODEL_ID)


def build_run_info(
    *,
    started_at: datetime,
    completed_at: datetime,
    status: str,
    prompt: PromptConfig,
    question_count: int,
    success_count: int,
    failure_count: int,
    mode: str,
    embedding_models: Sequence[str],
    provider_model: str,
    input_snapshot: Path | None,
    output_snapshot: Path,
    elapsed_seconds: float,
) -> str:
    if mode == "snapshot":
        recorded_models = ", ".join(embedding_models)
        embedding_value = (
            f"Not used (snapshot metadata: {recorded_models})"
            if recorded_models
            else "Not used"
        )
    else:
        embedding_value = ", ".join(embedding_models) if embedding_models else "Unknown"
    return "\n".join(
        [
            f"Started: {started_at.isoformat(timespec='seconds')}",
            f"Completed: {completed_at.isoformat(timespec='seconds')}",
            f"Status: {status}",
            f"Prompt Version: {prompt.version}",
            f"Prompt Path: {prompt.path}",
            f"RAG Template Path: {prompt.rag_template_path}",
            f"Question Count: {question_count}",
            f"Success Count: {success_count}",
            f"Failure Count: {failure_count}",
            f"Mode: {mode}",
            f"Embedding Model: {embedding_value}",
            f"Top-K: {TOP_K}",
            f"Use Reranker: {USE_RERANKER}",
            f"Remote LLM Model: {MODEL_ID}",
            f"Adapter: {provider_model} (Remote server routing key)",
            f"max_output_tokens: {MAX_OUTPUT_TOKENS}",
            "DB Write Enabled: False",
            f"Snapshot Input Path: {input_snapshot or 'None'}",
            f"Snapshot Path: {output_snapshot}",
            f"Elapsed Seconds: {elapsed_seconds:.3f}",
            "",
        ]
    )


async def run_evaluation(args: argparse.Namespace) -> int:
    """평가 준비부터 문항별 검색·생성·기록까지 전체 순서를 관리한다."""

    run_started_at = datetime.now().astimezone()
    run_timer = time.perf_counter()

    # 1. Prompt와 실행 모드별 질문을 검증한다.
    prompt_path, rag_template_path = resolve_prompt_sources(args)
    prompt = load_prompt_config(
        prompt_path,
        rag_template_path=rag_template_path,
    )
    if args.prompt_file is None and prompt.version != args.prompt_version:
        raise ValueError(
            f"선택한 preset({args.prompt_version})과 JSON version({prompt.version})이 다릅니다."
        )
    input_snapshot_path: Path | None = None
    source_snapshot: dict[str, Any] | None = None
    snapshot_rows_by_id: dict[str, SnapshotQuestion] = {}

    if args.mode == "snapshot":
        input_snapshot_path = args.snapshot.expanduser().resolve()
        source_snapshot, snapshot_questions = load_snapshot(input_snapshot_path)
        available_questions = [item.question for item in snapshot_questions]
        snapshot_rows_by_id = {
            item.question.question_id: item for item in snapshot_questions
        }
    else:
        available_questions = load_fixed_questions()

    questions = select_questions(
        available_questions,
        limit=args.limit,
        question_id=args.question_id,
    )

    # 2. 이번 실행 전용 로컬 결과 폴더와 빈 결과 파일을 만든다.
    output_dir = create_output_directory(args.output_root)
    version_slug = prompt_version_slug(prompt.version)
    result_path = output_dir / f"rag_{version_slug}_result.txt"
    debug_path = output_dir / f"rag_{version_slug}_debug.jsonl"
    snapshot_path = output_dir / "retrieval_snapshot.json"
    run_info_path = output_dir / "run_info.txt"
    result_path.write_text("", encoding="utf-8")
    debug_path.write_text("", encoding="utf-8")

    # 3. Live는 기존 Embedding Provider를 준비하고, Snapshot은 저장된 설정만 읽는다.
    if args.mode == "live":
        from app.core.config import settings
        from app.core.rag_embedding import get_default_rag_embedding_providers

        providers = get_default_rag_embedding_providers()
        embedding_models = [str(provider.name) for provider in providers]
        snapshot_payload: dict[str, Any] = {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "created_at": run_started_at.isoformat(timespec="seconds"),
            "prompt_version": prompt.version,
            "retrieval_config": {
                "top_k": TOP_K,
                "use_reranker": USE_RERANKER,
                "providers": embedding_models,
                "embedding_dimension": settings.embedding_dimension,
                "candidate_min": settings.embedding_search_candidates,
                "rrf_k": settings.embedding_rrf_k,
            },
            "questions": [],
        }
        write_json(snapshot_path, snapshot_payload)
    else:
        providers = []
        retrieval_config = (
            source_snapshot.get("retrieval_config", {}) if source_snapshot else {}
        )
        stored_models = retrieval_config.get(
            "providers", retrieval_config.get("embedding_models", [])
        )
        embedding_models = (
            [str(model) for model in stored_models]
            if isinstance(stored_models, list)
            else []
        )
        snapshot_payload = source_snapshot or {"questions": []}
        # 비교 실행 결과 폴더에도 입력 Snapshot을 내용 변경 없이 복사해 둔다.
        write_json(snapshot_path, snapshot_payload)

    model_definition = resolve_remote_model()
    success_count = 0
    failure_count = 0

    # 4. 한 문항이 실패해도 다음 문항의 평가를 계속한다.
    for position, question in enumerate(questions, start=1):
        question_timer = time.perf_counter()
        retrieval_elapsed = 0.0
        llm_elapsed: float | None = None
        chunks: list[Any] = []
        answer: str | None = None
        execution: Any | None = None
        error_stage: str | None = None
        error_type: str | None = None

        print(f"[{position}/{len(questions)}] {question.question_id}")

        # 4-1. Live 검색 또는 저장된 Snapshot 청크 복원
        retrieval_started = time.perf_counter()
        if args.mode == "live":
            print("  Retrieval...")
            try:
                chunks = retrieve_live(question.question, providers)
            except Exception as exc:  # 문항 단위 격리: 상세 메시지는 Secret 보호를 위해 기록하지 않는다.
                error_stage = "retrieval"
                error_type = type(exc).__name__
        else:
            snapshot_question = snapshot_rows_by_id[question.question_id]
            chunks = list(snapshot_question.chunks)
            if not snapshot_question.retrieval_success:
                error_stage = "retrieval_snapshot"
                error_type = snapshot_question.error_type or "RecordedRetrievalError"
        retrieval_elapsed = time.perf_counter() - retrieval_started
        serialized_contexts = serialize_chunks(chunks)

        if args.mode == "live":
            snapshot_payload["questions"].append(
                {
                    "question_id": question.question_id,
                    "category": question.category,
                    "question": question.question,
                    "retrieval_success": error_stage is None,
                    "error_type": error_type,
                    "retrieved_contexts": serialized_contexts,
                }
            )
            # LLM 실패와 무관하게 검색 직후 Snapshot을 먼저 남긴다.
            write_json(snapshot_path, snapshot_payload)

        if error_stage is None:
            print(f"  Retrieval completed: {len(chunks)} chunks")

            # 4-2. 기존 Context Builder와 JSON Prompt로 사용자 메시지를 구성한다.
            user_prompt = compose_user_prompt(prompt, chunks, question.question)

            # 4-3. 기존 LLM Application을 통해 Remote MedGemma를 호출한다.
            print("  LLM generating...")
            llm_started = time.perf_counter()
            try:
                execution = await generate_answer(prompt, user_prompt)
                answer = execution.result.answer
            except Exception as exc:
                # 문항 단위로 격리하고, 민감할 수 있는 예외 본문은 저장하지 않는다.
                error_stage = "llm"
                error_type = type(exc).__name__
            llm_elapsed = time.perf_counter() - llm_started

        total_elapsed = time.perf_counter() - question_timer
        success = error_stage is None
        if success:
            success_count += 1
            print(f"  Completed: {total_elapsed:.2f}s")
        else:
            failure_count += 1
            print(f"  Failed ({error_stage}: {error_type}): {total_elapsed:.2f}s")

        # 4-4. 사람이 읽는 TXT와 문항별 JSONL을 즉시 기록한다.
        append_result_text(
            result_path,
            question=question,
            contexts=serialized_contexts,
            answer=answer,
            prompt_version=prompt.version,
            retrieval_elapsed=retrieval_elapsed,
            llm_elapsed=llm_elapsed,
            total_elapsed=total_elapsed,
            error_stage=error_stage,
            error_type=error_type,
        )
        result = execution.result if execution is not None else None
        append_jsonl(
            debug_path,
            {
                "question_id": question.question_id,
                "category": question.category,
                "prompt_version": prompt.version,
                "mode": args.mode,
                "retrieval_count": len(serialized_contexts),
                "retrieval_elapsed_seconds": round(retrieval_elapsed, 6),
                "llm_elapsed_seconds": round(llm_elapsed, 6)
                if llm_elapsed is not None
                else None,
                "total_elapsed_seconds": round(total_elapsed, 6),
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "input_tokens": getattr(result, "input_tokens", None),
                "output_tokens": getattr(result, "output_tokens", None),
                "total_tokens": getattr(result, "total_tokens", None),
                "finish_reason": getattr(result, "finish_reason", None),
                "success": success,
                "error": (
                    {"stage": error_stage, "type": error_type}
                    if error_stage and error_type
                    else None
                ),
            },
        )

    # 5. 실행 전체 요약을 민감한 설정값 없이 기록한다.
    completed_at = datetime.now().astimezone()
    status = "completed" if failure_count == 0 else "completed_with_errors"
    run_info_path.write_text(
        build_run_info(
            started_at=run_started_at,
            completed_at=completed_at,
            status=status,
            prompt=prompt,
            question_count=len(questions),
            success_count=success_count,
            failure_count=failure_count,
            mode=args.mode,
            embedding_models=embedding_models,
            provider_model=model_definition.provider_model,
            input_snapshot=input_snapshot_path,
            output_snapshot=snapshot_path,
            elapsed_seconds=time.perf_counter() - run_timer,
        ),
        encoding="utf-8",
    )

    print(f"Results: {output_dir}")
    return 0 if failure_count == 0 else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return asyncio.run(run_evaluation(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        # 설정/입력 오류만 짧게 알린다. 외부 호출 예외는 문항 단위 기록에서 처리한다.
        print(f"실행 준비 실패: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
