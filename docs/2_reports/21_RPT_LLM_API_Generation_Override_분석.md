# LLM API Generation Parameter Override 가능 여부 분석

- 분석 기준일: 2026-09-04
- 분석 대상: 현재 Backend → Remote LLM Server 코드
- 분석 방식: 정적 코드 분석 및 로컬 Pydantic 기본 동작 확인
- 미수행: 코드 수정, Remote API 호출, 실제 모델 로드·추론, Vast.ai 파일·로그 확인

## 결론 요약

현재 구조는 요청한 분류 중 **B. 일부만 가능**이다.

```text
Backend 내부 ProviderGenerateRequest
→ max_output_tokens만 전달 가능
→ Remote /v1/generate가 수신
→ model.generate(max_new_tokens=...)에 적용
```

나머지 Generation parameter는 Remote Server 내부에 고정되어 있거나 명시되지 않았다.

```text
do_sample=True                  # 서버 고정
temperature=0.7                # 서버 고정
top_p=0.9                      # 서버 고정
repetition_penalty=1.12        # 서버 고정
no_repeat_ngram_size           # 서버에서 미설정
eos_token_id=tokenizer.eos_token_id
pad_token_id=tokenizer.pad_token_id
```

단, “Backend 요청”의 의미에 따라 한 단계 더 구분해야 한다.

| 경계 | 호출자가 변경 가능한 Generation 설정 |
| --- | --- |
| Remote Server `/v1/generate`를 직접 호출 | `max_output_tokens`만 가능 |
| Backend 내부에서 `ProviderGenerateRequest` 생성 | `max_output_tokens`만 가능 |
| 공개 Backend `/api/llm/generate` HTTP 요청 | 없음 |
| Admin `/api/admin/llm/run`, `/compare` HTTP 요청 | 없음 |
| 메인 상담 요청 | 외부 override 불가; Backend가 512를 고정 요청 |

공개 Backend API의 Pydantic schema에는 `max_output_tokens`도 없다. 따라서 Frontend나 외부 Client가 현재 Backend HTTP 요청에 Generation 설정을 넣어 변경하는 구조는 아직 구현되지 않았다.

EOS는 `tokenizer.eos_token_id` 하나만 전달한다. `<end_of_turn>`의 실제 Token ID를 조회하거나 별도 종료 ID로 추가하는 코드는 없다. 실제 tokenizer 파일도 저장소에 없어 EOS와 EOT가 같은 ID인지 다른 ID인지 현재 로컬 코드만으로 확정할 수 없다.

---

## 1. `/v1/generate` Request Schema

### 1.1 Endpoint 구현 위치

- 파일: `scripts/vastai_medical_llm_server.py`
- Endpoint: `POST /v1/generate`
- Endpoint 함수: `generate()`
- 동기 추론 함수: `_generate_sync()`
- 실행 방식: `await asyncio.to_thread(_generate_sync, request)`
- Notebook 연결: `scripts/vastai_medical_llm_server.ipynb`가 위 Python 모듈을 Uvicorn으로 실행한다.

```text
python -m uvicorn
vastai_medical_llm_server:app
--app-dir {PROJECT_ROOT}/scripts
--workers 1
```

Notebook 안에 별도의 Server 구현이 중복된 구조가 아니라, 현재 분석한 `.py` 파일이 실제 Uvicorn Application 진입점이다.

### 1.2 Message schema

```python
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=30_000)
```

| 필드 | 타입 | 필수 | 제약/기본값 |
| --- | --- | --- | --- |
| `role` | `system` / `user` / `assistant` | 예 | 다른 값은 validation 실패 |
| `content` | string | 예 | 1~30,000자 |

### 1.3 GenerateRequest schema

```python
class GenerateRequest(BaseModel):
    model: str
    messages: list[Message] = Field(min_length=1, max_length=50)
    max_output_tokens: int = Field(default=256, ge=1, le=512)
```

| 필드 | 타입 | 필수 | 제약/기본값 |
| --- | --- | --- | --- |
| `model` | string | 예 | 별도 길이/enum 제약 없음. 로드되지 않은 ID는 `_generate_sync()`에서 404 |
| `messages` | `list[Message]` | 예 | 1~50개 |
| `max_output_tokens` | integer | 아니오 | 기본 256, 최소 1, 최대 512 |

Authorization Bearer token은 JSON body가 아니라 `Authorization` Header로 검사한다.

### 1.4 알 수 없는 추가 필드 처리

`GenerateRequest`와 `Message`는 `extra="forbid"`를 설정하지 않았다. Pydantic의 기본 extra 처리에 따라 알 수 없는 필드는 validation error가 아니라 **무시되고 모델에서 제거된다**.

현재 로컬 환경의 Pydantic 2.13.4에서도 다음 동작을 확인했다.

```text
BaseModel.model_config.extra = None
알 수 없는 입력 필드 → model_dump() 결과에서 제거
```

따라서 다음 요청은 `do_sample`이 적용되지 않은 채 HTTP 처리에 성공할 수 있다.

```json
{
  "model": "medgemma-final",
  "messages": [{"role": "user", "content": "질문"}],
  "max_output_tokens": 256,
  "do_sample": false
}
```

`request.do_sample` 속성은 만들어지지 않으며 `_generate_sync()`는 계속 서버 고정값 `True`를 사용한다. 이 때문에 HTTP 200은 override 적용 증거가 아니다.

### 1.5 요청 Parameter 지원 표

| Parameter | API Request 지원 | 서버 내부 기본값 | `model.generate()` 전달 | Backend override 가능 |
| --- | --- | --- | --- | --- |
| `max_output_tokens` | 예 | 256, 허용 1~512 | `max_new_tokens=request.max_output_tokens` | 예, Backend 내부 계약에서만 |
| `max_new_tokens` | 아니오 | Request 필드 없음 | `max_output_tokens`에서 변환된 값만 전달 | 아니오 |
| `do_sample` | 아니오 | `True` 고정 | `do_sample=True` | 아니오 |
| `temperature` | 아니오 | `0.7` 고정 | `temperature=0.7` | 아니오 |
| `top_p` | 아니오 | `0.9` 고정 | `top_p=0.9` | 아니오 |
| `repetition_penalty` | 아니오 | `1.12` 고정 | `repetition_penalty=1.12` | 아니오 |
| `no_repeat_ngram_size` | 아니오 | 서버 코드에서 미설정 | 명시 전달하지 않음 | 아니오 |

`no_repeat_ngram_size`의 최종 유효값은 로드된 모델의 `generation_config` 또는 Transformers 기본값에 의해 정해진다. 현재 Server는 해당 값을 출력하지 않고 모델 파일도 저장소에 없으므로 실제 원격 모델의 유효값은 확인 필요다. 일반적인 Transformers 기본값은 0이지만, 모델의 `generation_config.json`이 값을 제공할 수 있으므로 현재 원격 모델에 대해 0이라고 단정하지 않는다.

---

## 2. Backend Request 구조

### 2.1 공통 내부 계약

파일: `ai/llm/contracts.py`

```python
@dataclass(frozen=True)
class ProviderGenerateRequest:
    messages: tuple[LlmMessage, ...]
    document_name: str | None = None
    max_output_tokens: int | None = None
```

현재 공통 LLM 계약이 표현할 수 있는 Generation 설정도 `max_output_tokens` 하나뿐이다. `do_sample`, `temperature`, `top_p`, `repetition_penalty`, `no_repeat_ngram_size` 필드는 없다.

### 2.2 RemoteHttpLlmProvider payload

파일: `ai/llm/providers/remote_http.py`

실제 payload 생성:

```python
payload = {
    "model": model.provider_model,
    "messages": [
        {"role": message.role, "content": message.content}
        for message in request.messages
    ],
}
if request.max_output_tokens is not None:
    payload["max_output_tokens"] = request.max_output_tokens
```

즉, Remote Server로 전달되는 body는 다음 형태다.

```json
{
  "model": "medgemma-final",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "max_output_tokens": 512
}
```

확인된 사항:

- `prompt`라는 단일 필드는 Remote Server에 보내지 않는다. 모든 입력은 `messages`로 변환한다.
- Backend public model ID `medgemma`는 Registry를 거쳐 기본 Remote ID `medgemma-final`로 바뀐다.
- `document_name`은 `ProviderGenerateRequest`에 있지만 `RemoteHttpLlmProvider` payload에는 포함되지 않는다.
- Generation 관련 payload는 `max_output_tokens` 하나뿐이다.
- API Key는 JSON이 아니라 HTTP Client의 Bearer Header에 들어간다.

### 2.3 Backend 호출 경로별 실제 값

| Backend 경로 | Request 생성 코드 | Remote로 보내는 `max_output_tokens` |
| --- | --- | --- |
| 메인 상담 `consult()` | `ProviderGenerateRequest(..., max_output_tokens=512)` | 512 |
| `POST /api/llm/generate` | `_to_core_request(messages)` | 필드 생략 → Server 기본 256 |
| `POST /api/llm/compare` | `_to_core_request(messages)` | 필드 생략 → Server 기본 256 |
| `POST /api/admin/llm/run` | `ProviderGenerateRequest.from_prompt(...)` | 필드 생략 → Server 기본 256 |
| `POST /api/admin/llm/compare` | `ProviderGenerateRequest.from_prompt(...)` | 필드 생략 → Server 기본 256 |

따라서 “현재 기본 설정”은 호출 경로마다 다르다.

- 메인 RAG 상담: Backend가 명시적으로 512 요청.
- 일반/Admin LLM API: Remote body에서 생략되어 Server 기본 256 사용.

### 2.4 외부 Client가 호출하는 Backend HTTP schema

일반 LLM schema:

```python
class LlmGenerateRequest(BaseModel):
    model_id: str
    messages: list[LlmMessageInput]
```

Admin 단일 실행 schema:

```python
class LlmRunRequest(AdminSchema):
    prompt: str
    model_id: str
    document_name: str | None
    document_names: list[str]
```

두 schema 모두 Generation parameter 필드가 없다. Admin 비교 schema의 `chunk_size`와 `overlap`은 OCR/표시 관련 값이며 LLM generation 설정이 아니다.

일반/Admin schema 역시 `extra="forbid"`를 사용하지 않으므로 외부 Client가 다음 값을 임의로 추가해도 일반적으로 무시된다.

```text
max_output_tokens
max_new_tokens
do_sample
temperature
top_p
repetition_penalty
no_repeat_ngram_size
```

결론적으로 Frontend → Backend HTTP 요청으로는 현재 `max_output_tokens`조차 override할 수 없다.

---

## 3. `model.generate()` 실제 설정

### 3.1 전달 경로

```text
POST /v1/generate JSON
→ FastAPI/Pydantic GenerateRequest
→ generate()
→ asyncio.to_thread(_generate_sync, request)
→ _prepare_messages()
→ _render_prompt()
→ tokenizer(..., truncation=True, max_length=MAX_INPUT_TOKENS)
→ generation_kwargs 구성
→ loaded.model.generate(**inputs, **generation_kwargs)
```

### 3.2 실제 kwargs

파일 `scripts/vastai_medical_llm_server.py`의 현재 코드:

```python
generation_kwargs = {
    "max_new_tokens": request.max_output_tokens,
    "do_sample": True,
    "temperature": 0.7,
    "top_p": 0.9,
    "repetition_penalty": 1.12,
    "use_cache": True,
    "pad_token_id": loaded.tokenizer.pad_token_id,
    "eos_token_id": loaded.tokenizer.eos_token_id,
}
```

MedGemma 요청에는 다음도 추가한다.

```python
remove_invalid_values=True
renormalize_logits=True
```

최종 호출:

```python
output = loaded.model.generate(
    **inputs,
    **generation_kwargs,
)
```

### 3.3 고정/요청 연동 구분

| 설정 | 최종 전달값 | 값의 출처 | 요청 override |
| --- | --- | --- | --- |
| `max_new_tokens` | `request.max_output_tokens` | API Request | 가능 |
| `do_sample` | `True` | Server 하드코딩 | 불가능 |
| `temperature` | `0.7` | Server 하드코딩 | 불가능 |
| `top_p` | `0.9` | Server 하드코딩 | 불가능 |
| `repetition_penalty` | `1.12` | Server 하드코딩 | 불가능 |
| `no_repeat_ngram_size` | 명시되지 않음 | model/default generation config | 불가능 |
| `eos_token_id` | `loaded.tokenizer.eos_token_id` | 런타임 Tokenizer | 불가능 |
| `pad_token_id` | `loaded.tokenizer.pad_token_id` | 런타임 Tokenizer | 불가능 |
| `use_cache` | `True` | Server 하드코딩 | 불가능 |
| `remove_invalid_values` | MedGemma만 `True` | Server model 조건 | 불가능 |
| `renormalize_logits` | MedGemma만 `True` | Server model 조건 | 불가능 |

`max_output_tokens`는 Hugging Face parameter 이름이 아니다. Server API가 사용하는 외부 이름이며 내부에서 `max_new_tokens`로 정확히 변환된다.

---

## 4. EOS / End-of-turn 설정

### 4.1 Tokenizer 로딩

Server는 Adapter tokenizer를 직접 로드하지 않고 Base tokenizer를 로드한다.

```text
AutoTokenizer.from_pretrained(base_dir, local_files_only=True)
```

Adapter에 `chat_template.jinja`가 존재하면 그 Text만 Base tokenizer의 `chat_template`에 덮어쓴다.

```text
Base tokenizer vocabulary/special token IDs
+
Adapter chat_template.jinja
```

`pad_token_id`가 `None`이면 다음 코드로 EOS token을 padding token으로 사용한다.

```python
if tokenizer.pad_token_id is None:
    tokenizer.pad_token = tokenizer.eos_token
```

따라서 최종 `pad_token_id`는 기존 Base pad ID 또는 fallback된 EOS ID다.

### 4.2 현재 종료 조건

현재 `model.generate()`에 명시적으로 전달되는 종료 설정은 다음 하나다.

```python
eos_token_id=loaded.tokenizer.eos_token_id
```

코드상 확인 결과:

- `tokenizer.eos_token_id`: 사용함. 숫자는 런타임 값이라 현재 저장소에서 확인 불가.
- `<end_of_turn>` 문자열: 학습 Notebook에는 존재하지만 Server Python 코드에는 없음.
- `convert_tokens_to_ids("<end_of_turn>")`: 호출하지 않음.
- `tokenizer.all_special_tokens`/`all_special_ids`: 확인하지 않음.
- 복수 `eos_token_id` list: 사용하지 않음.
- custom `StoppingCriteria`: 없음.
- stop string: 없음.

Hugging Face Transformers는 `eos_token_id`에 단일 ID뿐 아니라 여러 ID의 list도 지원하지만, 현재 프로젝트는 단일 `tokenizer.eos_token_id`만 전달한다. [Hugging Face Generation 문서](https://huggingface.co/docs/transformers/main/main_classes/text_generation)

### 4.3 `<end_of_turn>` 적용 여부 판단

현재 코드만 기준으로는 **별도의 `<end_of_turn>` 종료 조건을 적용하지 않는다.**

다만 다음 두 가능성을 구분해야 한다.

1. Base tokenizer의 `eos_token_id`가 곧 `<end_of_turn>` ID인 경우: 현재 단일 EOS 설정만으로도 EOT에서 종료될 수 있다.
2. EOS와 `<end_of_turn>`이 서로 다른 ID인 경우: 모델이 EOT를 생성해도 그 토큰 때문에 즉시 종료된다고 보장할 수 없다.

어느 경우인지는 실제 `MODEL_ROOT/base/medgemma` tokenizer 파일 또는 실행 중 Tokenizer 객체를 확인해야 한다. 저장소에는 `models/`가 없고 Token ID를 출력하는 Server log/debug endpoint도 없다. 따라서 숫자 ID를 추정해서는 안 된다.

학습 Notebook에서 `<end_of_turn>` 문자열을 Prompt에 사용했다는 사실은 runtime tokenizer의 EOS mapping을 증명하지 않는다.

### 4.4 반복/다음 대화 생성 위험

EOS와 EOT가 다르다면 다음 가능성이 있다.

```text
assistant가 <end_of_turn> 생성
→ EOT가 eos_token_id에 포함되지 않음
→ generate()가 계속 진행
→ 다음 role/turn 형태 Text 또는 반복 출력 가능
→ 결국 EOS 또는 max_new_tokens에서 종료
```

이는 코드 구조에서 도출한 위험이며 실제 원격 tokenizer 상태가 확인되지 않았으므로 발생 여부는 확인 필요다. `decode(..., skip_special_tokens=True)`는 생성된 special token을 출력 Text에서 숨길 수 있어, 응답 Text만 보고 EOT 생성 여부를 판단하기도 어렵다.

### 4.5 현재 `finish_reason`의 한계

Server는 다음 기준만 사용한다.

```python
"length" if output_tokens >= request.max_output_tokens else "stop"
```

따라서 `finish_reason="stop"`은 다음을 구분하지 못한다.

- 일반 EOS에서 종료
- `<end_of_turn>`이 EOS와 같은 ID라 종료
- 다른 내부 종료 조건

또한 요청 한도와 같은 개수의 마지막 token이 EOS였더라도 단순 길이 비교상 `length`로 기록될 수 있다. 현재 응답 metadata만으로 실제 종료 Token ID를 알 수 없다.

---

## 5. 각 Generation Parameter override 가능 여부

### 5.1 경계별 상세표

| Parameter | Remote `/v1/generate` 직접 요청 | Backend 내부 `ProviderGenerateRequest` | 공개 Backend HTTP 요청 | 실제 `model.generate()` |
| --- | --- | --- | --- | --- |
| `max_output_tokens` | 가능 | 가능 | 불가능 | `max_new_tokens`로 적용 |
| `max_new_tokens` | 불가능, extra로 무시 | 필드 없음 | 필드 없음/무시 | API 값으로 직접 받지 않음 |
| `do_sample` | 불가능, extra로 무시 | 필드 없음 | 필드 없음/무시 | `True` 고정 |
| `temperature` | 불가능, extra로 무시 | 필드 없음 | 필드 없음/무시 | `0.7` 고정 |
| `top_p` | 불가능, extra로 무시 | 필드 없음 | 필드 없음/무시 | `0.9` 고정 |
| `repetition_penalty` | 불가능, extra로 무시 | 필드 없음 | 필드 없음/무시 | `1.12` 고정 |
| `no_repeat_ngram_size` | 불가능, extra로 무시 | 필드 없음 | 필드 없음/무시 | 미명시 |
| `eos_token_id` | 불가능 | 필드 없음 | 필드 없음/무시 | Tokenizer 값 고정 사용 |
| `pad_token_id` | 불가능 | 필드 없음 | 필드 없음/무시 | Tokenizer 값 고정 사용 |

### 5.2 A/B/C 최종 판정

**B. 일부만 가능**

근거:

1. `max_output_tokens`는 Backend Core 계약에 존재한다.
2. `RemoteHttpLlmProvider`가 이를 Remote JSON body에 전달한다.
3. Remote Server가 이를 validation한다.
4. `_generate_sync()`가 `max_new_tokens=request.max_output_tokens`로 실제 `model.generate()`에 전달한다.
5. 나머지 요청 대상 설정은 API/Core 계약에 없고 Server에서 고정 또는 미설정이다.

단, Frontend/외부 Client → 공개 Backend HTTP API의 관점만 좁게 보면 **현재 override 가능한 설정이 없으므로 C에 가깝다.** 전체 Backend-to-Remote 구조 분류는 내부 계약에서 한 항목이 끝까지 전달되므로 B가 정확하다.

---

## 6. 코드 수정 없이 가능한 테스트

### 6.1 전제

동일 조건으로 다음을 고정한다.

```text
model = medgemma-final
messages / Prompt = 동일
RAG Context = 동일 Snapshot
호출 순서와 반복 횟수 기록
Server revision / Adapter revision 기록
```

현재 `do_sample=True`라 seed도 요청으로 고정할 수 없다. 따라서 동일 Prompt의 한 번씩 결과 차이를 설정 효과로 단정하면 안 된다.

### 6.2 Test A — 현재 기본 설정

호출 경로를 먼저 고정해야 한다.

일반/Admin LLM API를 사용할 경우:

```text
Backend가 max_output_tokens를 보내지 않음
→ Remote Server 기본 256
→ 나머지 값은 Server 고정 sampling 설정
```

메인 상담 경로를 사용할 경우:

```text
consult()가 max_output_tokens=512 전달
→ Remote Server max_new_tokens=512
→ 나머지 값은 Server 고정 sampling 설정
```

두 경로를 섞으면 Test A의 기준부터 달라지므로 같은 경로만 사용한다.

### 6.3 Test B — 현재 API가 지원하는 범위

현재 가능한 Test B는 아래 한 항목뿐이다.

```text
max_output_tokens=256
```

방법 후보:

- 평가 스크립트에서 `ProviderGenerateRequest(max_output_tokens=256)`을 만들어 `llm_application.run()` 직접 호출.
- 또는 Remote `/v1/generate`에 `max_output_tokens=256` 직접 전달.

다음 Stable Generation 요청 전체는 현재 적용할 수 없다.

```text
do_sample=false                # 무시됨, 실제 값은 True
max_output_tokens=256          # 적용됨
repetition_penalty=1.10        # 무시됨, 실제 값은 1.12
no_repeat_ngram_size=4         # 무시됨, 실제 유효값 확인 필요
```

즉 현재 코드로 수행하면 “Stable Generation Test B”가 아니라 **출력 token 상한만 256으로 바꾼 기존 sampling Test**가 된다.

### 6.4 `do_sample=false`일 때 temperature/top_p

향후 `do_sample=false`가 실제 적용되면 기본 `num_beams=1` 조건에서 greedy decoding을 사용한다. `temperature`는 공식 문서상 `do_sample=True`가 필요하며, `top_p`도 sampling 후보 분포를 자르는 설정이므로 greedy token 선택에는 영향을 주지 않는다. [Hugging Face Text generation 문서](https://huggingface.co/docs/transformers/llm_tutorial)

따라서 Stable 설정에서는 다음 중 하나가 명확하다.

- `do_sample=false`일 때 `temperature`와 `top_p`를 `model.generate()` kwargs에서 제외한다.
- API에 값이 있더라도 “수신됐지만 비활성”으로 applied config에 표시한다.

반면 `repetition_penalty`와 `no_repeat_ngram_size`는 logits processor 계열 제약이므로 greedy decoding에서도 별도로 적용될 수 있다.

### 6.5 수정 없이 확인 가능한 범위

현재 코드 변경 없이 확인 가능한 항목:

- `/openapi.json`의 `GenerateRequest` schema로 허용 필드 확인.
- Server Source로 `generation_kwargs` 고정값 확인.
- `max_output_tokens`를 매우 작은 값으로 달리해 응답의 `output_tokens` 상한과 `finish_reason` 비교.
- 동일 Prompt를 여러 번 호출해 현재 sampling의 출력 변동 관찰.
- Vast.ai 유지보수 shell에서 실제 local tokenizer 파일의 EOS/EOT ID를 read-only로 조회.

현재 코드 변경 없이 확인할 수 없는 항목:

- 요청마다 `model.generate()` 직전에 계산된 전체 kwargs의 Server log.
- HTTP 응답에서 실제 적용된 Generation config.
- 어떤 Token ID가 종료를 일으켰는지.
- 무시된 extra field가 적용된 것처럼 보이지 않는다는 runtime 명시 응답.

---

## 7. 실제 override 적용 검증 방법

### 7.1 현재 구현 상태

현재 Server log는 모델 로딩, GPU 정보, 예외만 기록한다. 요청별 `generation_kwargs`를 출력하지 않는다.

현재 `/v1/generate` 응답:

```json
{
  "answer": "...",
  "input_tokens": 0,
  "output_tokens": 0,
  "total_tokens": 0,
  "finish_reason": "stop 또는 length",
  "gpu": 1
}
```

다음 값은 응답에 없다.

```text
applied_generation_config
requested_generation_config
stop_token_id
eos_token_ids
```

따라서 HTTP 200과 답변 Text만으로는 `do_sample`, penalty, EOT 설정의 실제 적용을 증명할 수 없다.

### 7.2 권장 검증 우선순위

다음 구현 단계에서는 아래 중 최소 하나가 필요하다.

#### 방법 1 — `model.generate()` 직전 Server log

`_generate_sync()`에서 최종 `generation_kwargs`를 만든 직후 안전한 설정값만 구조화 로그로 기록한다.

기록 대상:

```text
request/model ID
max_new_tokens
do_sample
temperature 활성/비활성
top_p 활성/비활성
repetition_penalty
no_repeat_ngram_size
eos_token_id 목록
pad_token_id
```

Prompt, API Key, 사용자 Text, 전체 답변은 기록하지 않는다.

#### 방법 2 — API debug response

관리자/평가 요청에서만 opt-in 가능한 debug mode를 두고 다음을 응답한다.

```json
{
  "applied_generation_config": {
    "max_new_tokens": 256,
    "do_sample": false,
    "temperature": null,
    "top_p": null,
    "repetition_penalty": 1.1,
    "no_repeat_ngram_size": 4,
    "eos_token_id": [0],
    "pad_token_id": 0
  }
}
```

숫자 `0`은 형식 예시일 뿐 실제 MedGemma Token ID가 아니다.

#### 방법 3 — debugger/직전 값 확인

Vast.ai에서 `_generate_sync()`의 `loaded.model.generate()` 직전에 breakpoint를 걸어 `generation_kwargs`와 Tokenizer ID를 확인한다. 운영 요청을 멈출 수 있으므로 별도 테스트 인스턴스에서만 수행한다.

### 7.3 EOS/EOT runtime 확인 항목

실제 Server의 MedGemma tokenizer로 다음을 확인해야 한다.

```text
tokenizer.eos_token
tokenizer.eos_token_id
tokenizer.pad_token
tokenizer.pad_token_id
tokenizer.unk_token_id
tokenizer.all_special_tokens
tokenizer.all_special_ids
tokenizer.convert_tokens_to_ids("<end_of_turn>")
model.generation_config.eos_token_id
실제 적용한 eos_token_id 목록
```

EOT ID가 `None`, unknown ID이거나 special token이 아니면 종료 목록에 임의로 넣지 않는다. EOS와 같은 ID라면 중복 제거한다.

---

## 8. 수정이 필요하다면 최소 변경 위치

아직 수정하지 않는다. 전체 Backend HTTP 요청부터 Server `model.generate()`까지 override하려면 최소 변경 경계는 다음과 같다.

### 8.1 필수 변경 위치

| 순서 | 파일 | 최소 변경 책임 |
| --- | --- | --- |
| 1 | `backend/app/schemas/llm.py` | 공개 일반 LLM Request에 허용 Generation 필드 추가 |
| 2 | `backend/app/schemas/admin.py` | Admin run/compare에서도 필요하면 동일 필드 추가 |
| 3 | `backend/app/services/llm_service.py` | HTTP schema 값을 Core Request로 전달 |
| 4 | `backend/app/services/admin_llm.py` | Admin schema 값을 Core Request로 전달 |
| 5 | `ai/llm/contracts.py` | `ProviderGenerateRequest`에 공통 Generation 계약 추가 |
| 6 | `ai/llm/providers/remote_http.py` | 허용 필드만 Remote JSON payload에 추가 |
| 7 | `scripts/vastai_medical_llm_server.py` | `GenerateRequest` validation 및 `_generate_sync()` kwargs override |

평가 스크립트가 공개 Backend API를 거치지 않고 `llm_application.run()`을 직접 호출한다면 1~4번은 해당 실험에는 생략할 수 있다. 그러나 Server와 Core 계약인 5~7번은 필요하다.

### 8.2 Server 최소 변경 개념

Server `GenerateRequest`가 선택적으로 표현해야 할 후보:

```text
max_output_tokens
do_sample
temperature
top_p
repetition_penalty
no_repeat_ngram_size
```

`_generate_sync()`에서는 다음 정책이 필요하다.

```text
요청값이 있으면 validation 후 적용
요청값이 없으면 현재 Server 기본값 유지
do_sample=false이면 temperature/top_p를 비활성으로 처리
모델별 안전 상한 유지
최종 applied config를 log 또는 debug response로 확인
```

임의의 `generation_kwargs: dict` 전체를 그대로 `model.generate()`에 넘기는 방식은 권장하지 않는다. 허용 목록과 범위 validation 없이 GPU memory·응답 시간·출력 크기에 영향을 주는 설정까지 외부에서 바꿀 수 있기 때문이다.

### 8.3 EOS/EOT는 별도 최소 수정

Generation override와 별개로 MedGemma 종료 문제를 해결하려면 `scripts/vastai_medical_llm_server.py`에서 실제 Tokenizer를 확인한 뒤 MedGemma에만 유효한 종료 ID 목록을 구성해야 한다.

```text
[tokenizer.eos_token_id, valid_end_of_turn_token_id]
→ None/unknown/중복 제거
→ model.generate(eos_token_id=stop_token_ids)
```

Transformers는 복수 EOS ID를 지원한다. 다만 실제 `<end_of_turn>` ID는 저장소 코드로 확인되지 않았으므로 숫자를 하드코딩하면 안 된다. [Hugging Face Generation utilities](https://huggingface.co/docs/transformers/internal/generation_utils)

### 8.4 최종 권장안

현재 가능한 A/B 테스트는 `max_output_tokens` 비교로 한정한다. 요청한 Stable Generation 설정 전체를 검증하려면 다음 순서가 최소다.

1. 실제 MedGemma tokenizer의 EOS/EOT 관계 확인.
2. Server Request schema와 `generation_kwargs`에 허용 필드 추가.
3. Core `ProviderGenerateRequest`와 Remote payload에 같은 필드 추가.
4. 필요한 경우 공개 Backend API schema까지 노출.
5. `model.generate()` 직전 applied config를 안전하게 기록.
6. 동일 Prompt/RAG Snapshot으로 기본 설정과 Stable 설정을 반복 비교.

현재 상태에서 unsupported field를 JSON에 추가해 HTTP 200을 받는 방식은 Stable 설정 검증이 아니다. 적용 가능한 유일한 request-level override는 `max_output_tokens`다.
