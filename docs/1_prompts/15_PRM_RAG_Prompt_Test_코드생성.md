좋아. 이번에는 **기존 dev 프로젝트의 RAG 코드를 그대로 재사용하는 평가용 실행 파일 하나**만 만들게 하자. 핵심은 **DB Write 없이 조회만**, 그리고 **RAG 검색 결과를 Snapshot으로 남겨서 이후 V4.2 비교에 재사용**하는 거야.

# RAG 프롬프트 평가용 실행 파일 구현 지시문

## 1. 작업 목적

현재 dev 프로젝트에는 다음 RAG 기능이 이미 구현되어 있다.

```text
사용자 질문
→ 질문 Embedding 생성
→ Neon Vector DB 검색
→ Top-K Chunk 반환
→ Context 구성
→ Remote MedGemma 호출
→ 응답 반환
```

이번 작업의 목적은 새로운 RAG를 구현하는 것이 아니다.

기존 dev 프로젝트의 RAG 관련 코드를 최대한 그대로 재사용하여,
고정 질문 약 5개에 대해 다음 테스트를 수행할 수 있는
**단일 Python 실행 파일**을 추가한다.

```text
질문
→ 기존 RAG 검색
→ Top-K Context 확보
→ 지정 RAG Prompt 적용
→ 기존 Remote MedGemma 호출
→ 결과 TXT 저장
→ Debug JSONL 저장
→ Retrieval Snapshot JSON 저장
```

---

# 2. 선행 분석 결과

기존 분석 결과를 기준으로 다음 구조를 우선 재사용한다.

대표적으로 확인된 구성:

```text
rag_search_service.search()
build_reference_info_block()
llm_application.run()
```

실제 프로젝트에서 함수명/경로가 다르면
반드시 현재 코드 기준으로 다시 확인하여 import한다.

중요:

> 기존 코드를 복사하여 별도 RAG를 새로 구현하지 않는다.

기존 Service / Repository / DB connection / Embedding logic을 그대로 재사용한다.

---

# 3. 매우 중요한 제한

이번 테스트 파일에서는 Neon DB에 데이터를 새로 저장하면 안 된다.

## 절대 금지

- 문서 INSERT
- Chunk INSERT
- Embedding INSERT
- 사용자 질문 INSERT
- LLM 답변 INSERT
- 상담 로그 INSERT
- UPDATE
- DELETE
- UPSERT
- 테스트 데이터를 Neon에 저장
- MessageService.send_message() 사용

특히 기존 분석 결과에서:

```text
MessageService.send_message()
```

는 사용자 질문/답변 등을 DB에 저장할 수 있으므로
이번 평가 스크립트에서는 사용하지 않는다.

---

# 4. 허용되는 DB 작업

다음만 허용한다.

```text
질문 Embedding 생성
→ 메모리에서 사용

기존 Neon Vector DB
→ SELECT / Vector similarity search

기존 Document / Chunk
→ READ

Top-K Retrieval
→ READ
```

질문 Embedding은 검색에만 사용하고 DB에 저장하지 않는다.

---

# 5. 생성할 파일

가능하면 다음 파일 하나만 추가한다.

```text
scripts/rag_prompt_eval.py
```

프로젝트 구조상 `scripts/`가 적절하지 않다면
기존 구조를 분석해서 가장 적절한 위치를 사용한다.

단, 평가 실행 파일 외의 기존 서비스 코드는
가능하면 수정하지 않는다.

---

# 6. 실행 파일의 역할

`rag_prompt_eval.py`는 다음 흐름으로 동작한다.

```text
main()
│
├─ 환경변수 / 설정 로드
├─ 기존 DB / Embedding / RAG Service 준비
├─ Prompt 파일 로드
│
├─ 고정 질문 반복
│   ├─ 질문 Embedding
│   ├─ 기존 Neon Vector 검색
│   ├─ Top-K Retrieval
│   ├─ Context 구성
│   ├─ RAG Prompt 구성
│   ├─ Remote MedGemma 호출
│   ├─ 응답 수집
│   └─ 결과 기록
│
├─ Retrieval Snapshot 저장
├─ TXT 결과 저장
├─ JSONL Debug 저장
└─ 종료
```

---

# 7. 고정 질문

우선 테스트용 질문 5개를 코드 상단에서 쉽게 수정할 수 있도록 한다.

예:

```python
QUESTIONS = [
    {
        "id": "rag_01",
        "category": "consultation",
        "question": "식사 후 속이 쓰리고 신물이 올라옵니다. 어떤 원인이 있을 수 있나요?"
    },
    {
        "id": "rag_02",
        "category": "consultation",
        "question": "어제부터 기침과 가래가 심합니다. 어떻게 해야 하나요?"
    },
    {
        "id": "rag_03",
        "category": "ambiguous",
        "question": "요즘 손발이 가끔 저립니다. 어떤 원인 때문일 수 있나요?"
    },
    {
        "id": "rag_04",
        "category": "urgent",
        "question": "숨을 쉬기가 매우 힘들고 가슴이 답답합니다. 집에서 조금 기다려봐도 될까요?"
    },
    {
        "id": "rag_05",
        "category": "urgent",
        "question": "검은색 변을 봤고 어지럽고 식은땀이 납니다. 어떻게 해야 하나요?"
    },
]
```

단, 질문 목록은 별도 상수 또는 JSON으로 쉽게 교체 가능하게 만든다.

---

# 8. Prompt 입력

RAG Prompt는 코드에 하드코딩하지 않는다.

Prompt JSON 경로를 지정할 수 있도록 한다.

예:

```python
PROMPT_PATH = "..."
```

또는 CLI:

```bash
python scripts/rag_prompt_eval.py --prompt-file medical_prompt_v4.1_rag_prototype.json
```

Prompt JSON에서 최소한 다음 값을 읽을 수 있게 한다.

```text
version
system_prompt
rag_context_template
```

실제 V4.1 JSON 구조를 확인한 뒤 맞춘다.

Prompt 버전도 결과 파일에 기록한다.

---

# 9. RAG Context 구성

기존 프로젝트에 이미 Context 구성 함수가 있다면
그 함수를 우선 사용한다.

예:

```text
build_reference_info_block()
```

직접 새로운 형식을 만들지 않는다.

다만 최종 LLM 입력에서 최소한 다음 구분이 명확해야 한다.

```text
System Prompt
+
RAG Reference / Context
+
User Question
```

검색 문서와 사용자 질문의 경계가 명확한지 확인한다.

---

# 10. Retrieval 결과 저장

각 질문마다 실제 Top-K 결과를 저장한다.

최소한 다음 값 중
현재 실제 Retrieval 결과에서 제공되는 값만 기록한다.

```text
question_id
question
rank
chunk_id
document_id
content
source
title
url
score
distance
metadata
```

없는 필드를 임의 생성하지 않는다.

---

# 11. Retrieval Snapshot

첫 실행에서 실제 Neon 검색 결과를 다음 파일로 저장한다.

```text
outputs/rag_eval/<timestamp>/
    retrieval_snapshot.json
```

예상 구조:

```json
{
  "prompt_version": "v4.1",
  "questions": [
    {
      "question_id": "rag_01",
      "question": "...",
      "retrieved_contexts": [
        {
          "rank": 1,
          "content": "...",
          "source": "...",
          "score": 0.0
        }
      ]
    }
  ]
}
```

실제 필드는 Retrieval 반환 구조에 맞춘다.

이 Snapshot은 이후 V4.2 Prompt 테스트에서
Neon을 다시 조회하지 않고 동일 검색 결과를 사용하기 위한 것이다.

---

# 12. Live / Snapshot Mode

가능하면 두 가지 실행 모드를 지원한다.

## Live Mode

```text
질문
→ 실제 Embedding
→ 실제 Neon 검색
→ Snapshot 저장
→ LLM
```

예:

```bash
python scripts/rag_prompt_eval.py --mode live
```

## Snapshot Mode

```text
기존 retrieval_snapshot.json
→ Neon 검색 없음
→ Embedding 생성 없음
→ 동일 Context
→ LLM만 실행
```

예:

```bash
python scripts/rag_prompt_eval.py \
  --mode snapshot \
  --snapshot outputs/.../retrieval_snapshot.json
```

Snapshot Mode는 V4.1 / V4.2 Prompt 비교에 사용한다.

---

# 13. Remote LLM 호출

현재 프로젝트의 기존 LLM Application / Provider를 재사용한다.

새로운 Hugging Face 모델을 이 파일에서 직접 로드하지 않는다.

현재 서비스 구조:

```text
RAG Context
→ 기존 Remote LLM API
→ MedGemma
```

를 그대로 사용한다.

---

# 14. Generation 설정 관련

현재 Remote LLM API 분석 결과,
Backend에서 모든 Generation Parameter를 Override할 수 없는 상태이다.

따라서 이번 파일에서:

```text
do_sample
temperature
top_p
repetition_penalty
no_repeat_ngram_size
EOS / EOT
```

를 억지로 새로 구현하거나 전달하지 않는다.

현재 Remote LLM Server 설정을 사용한다.

단,

```text
max_output_tokens
```

가 기존 API에서 정상적으로 지원되고,
테스트 호출에서 직접 지정 가능하다면
기본값을 다음처럼 설정한다.

```python
MAX_OUTPUT_TOKENS = 256
```

불가능하면 현재 프로젝트 기본값을 사용한다.

결과 파일에는 실제 사용한 값 또는 확인 가능한 값을 기록한다.

---

# 15. 결과 TXT

사람이 읽기 쉬운 결과 파일을 저장한다.

예:

```text
outputs/rag_eval/20260904_153000/
    rag_v4.1_result.txt
```

각 질문마다 다음 형태로 작성한다.

```text
==================================================
Question ID: rag_01
Category: consultation
Question:
식사 후 속이 쓰리고 신물이 올라옵니다.

[Retrieval]

Top 1
Source:
Score:
Content:
...

Top 2
...

[Final Answer]

...

[Runtime]

Prompt Version:
Retrieval Count:
LLM Elapsed:
Total Elapsed:
==================================================
```

---

# 16. Debug JSONL

다음 파일도 저장한다.

```text
rag_v4.1_debug.jsonl
```

문항별 한 줄 JSON.

가능한 값:

```json
{
  "question_id": "rag_01",
  "category": "consultation",
  "prompt_version": "v4.1",
  "retrieval_count": 5,
  "retrieval_elapsed_seconds": 0.0,
  "llm_elapsed_seconds": 0.0,
  "total_elapsed_seconds": 0.0,
  "max_output_tokens": 256,
  "success": true,
  "error": null
}
```

현재 코드에서 확인 가능한 값만 기록한다.

---

# 17. 결과 디렉터리

실행마다 timestamp 폴더를 생성한다.

예:

```text
outputs/
└─ rag_eval/
   └─ 20260904_153000/
      ├─ rag_v4.1_result.txt
      ├─ rag_v4.1_debug.jsonl
      ├─ retrieval_snapshot.json
      └─ run_info.txt
```

---

# 18. run_info.txt

실행 환경을 기록한다.

최소:

```text
Started
Completed
Prompt Version
Prompt Path
Question Count
Mode
Embedding Model
Top-K
Remote LLM Model
Adapter
max_output_tokens
DB Write Enabled: False
Snapshot Path
Elapsed Seconds
```

실제 확인 가능한 정보만 기록한다.

---

# 19. DB Write 안전장치

가능하면 코드에 명시적인 주석과 검증을 넣는다.

예:

```python
# READ-ONLY RAG EVALUATION
# This script must not call document/chunk/message save functions.
```

테스트 스크립트에서 DB Write 관련 Repository 또는 Service는
import하지 않는 방향을 우선한다.

---

# 20. 첫 실행 안전 모드

전체 5문항을 바로 돌리기 전에
질문 하나만 실행할 수 있도록 옵션을 제공한다.

예:

```bash
python scripts/rag_prompt_eval.py \
  --mode live \
  --limit 1
```

또는:

```bash
--question-id rag_01
```

첫 테스트에서는:

```text
질문 1개
→ Retrieval
→ Context
→ Remote LLM
→ 로컬 파일 저장
```

까지만 확인한다.

문제가 없으면 이후 전체 5문항을 실행한다.

---

# 21. 오류 처리

한 질문에서 실패하더라도 전체 프로그램이 즉시 종료되지 않도록 한다.

예:

```text
rag_01 성공
rag_02 실패
rag_03 성공
...
```

실패 내용은:

```text
debug JSONL
run_info
console
```

에 기록한다.

Secret / DB Password / API Key는 출력하지 않는다.

---

# 22. Console 출력

실행 상태를 간단히 확인할 수 있도록 한다.

예:

```text
[1/5] rag_01
Embedding...
Retrieval completed: 5 chunks
LLM generating...
Completed: 18.32s

[2/5] rag_02
...
```

검색된 문서 전체를 콘솔에 대량 출력하지 않는다.

---

# 23. 구현 후 정적 점검

코드를 작성한 뒤 아직 실행하지 말고
먼저 다음을 자체 점검한다.

## DB Write 검사

`rag_prompt_eval.py`에서 다음 계열 호출이 없는지 확인:

```text
INSERT
UPDATE
DELETE
UPSERT
save_message
save_document
save_chunk
save_embedding
MessageService.send_message
```

## RAG 재사용 검사

기존:

```text
Embedding Service
RAG Search Service
Repository
Context Builder
LLM Application
```

을 import해서 사용하고 있는지 확인한다.

중복 구현이 있으면 가능한 범위에서 기존 모듈 사용으로 수정한다.

---

# 24. 이번 작업에서 하지 않을 것

다음은 이번 작업 범위가 아니다.

- V4.2 Prompt 작성
- Prompt 품질 분석
- Remote LLM Server Generation 설정 수정
- Backend API Schema 수정
- RAG 알고리즘 수정
- Embedding 모델 변경
- Top-K 튜닝
- Neon 데이터 추가
- DB Schema 변경
- Frontend 수정
- 운영 서비스 코드 리팩터링

---

# 25. 최종 산출물

## 코드

```text
scripts/rag_prompt_eval.py
```

또는 실제 프로젝트 구조상 가장 적절한 단일 실행 파일.

## 보고서

```text
RAG_프롬프트_평가스크립트_구현보고.md
```

보고서에는 다음을 기록한다.

1. 생성 파일
2. 재사용한 기존 모듈
3. 전체 실행 흐름
4. DB Read / Write 여부
5. Prompt 로딩 방식
6. Live Mode
7. Snapshot Mode
8. 출력 파일 구조
9. Remote LLM 호출 구조
10. max_output_tokens 처리
11. 실행 방법
12. 첫 1문항 테스트 명령
13. 전체 5문항 테스트 명령
14. 확인된 제한 사항
15. 실제 실행 전 확인해야 할 항목

---

# 최종 목표

최종적으로 다음이 가능해야 한다.

```text
[1차]

V4.1 Prompt
+
질문 5개
+
실제 dev RAG
+
기존 Neon 문서
+
현재 Remote MedGemma

→ 결과 저장
→ Retrieval Snapshot 저장
```

그리고 이후:

```text
[2차]

동일 Retrieval Snapshot
+
V4.2 Prompt

→ Neon 재조회 없이 실행
→ V4.1 / V4.2 비교
```

이번 작업은 **RAG 시스템 개발이 아니라 기존 RAG 구조를 이용한 READ-ONLY 프롬프트 평가 도구 구현**이다.

```

이걸로 구현한 다음에는 바로 5개를 돌리지 말고, **`--limit 1`이나 `--question-id rag_01`로 한 문항만 먼저 실행**하는 게 좋아. 그 한 번에서 Retrieval 결과가 실제로 나오고, Neon에 쓰기가 없고, Context가 Remote MedGemma까지 전달되는지만 확인한 다음 전체 5문항으로 넘어가면 돼.
```
