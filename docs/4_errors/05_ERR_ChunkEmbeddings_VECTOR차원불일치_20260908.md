# ChunkEmbeddings ORM·저장 계약 VECTOR 차원 불일치

> 상태: DEFECT-01 확인 완료, 미조치. 코딩 비허가 조건에 따라 Production 코드는 수정하지 않고 정적 분석과 단위 계약 테스트 결과만 기록한다.

- 작성일: 2026-09-08
- 결함 ID: `DEFECT-01`
- 대상 기능: RAG Chunk Embedding 저장·검색, Alembic schema 비교
- 직접 증상: `AssertionError: 2048 != 1024`
- 영향 범위: `ChunkEmbeddings` ORM metadata, Alembic autogenerate, 환경별 DB schema 정합성
- 비영향 범위: 이번 조사에서 Production 코드·Migration·테스트 코드는 변경하지 않음

---

## 1. 결론

`vector_db.chunk_embeddings.embedding`의 현재 차원 계약은 최신 Migration, 저장 Service, Repository 모두 `1024`다. 그러나 SQLAlchemy ORM 모델만 과거 계약인 `VECTOR(2048)`을 유지하고 있다.

따라서 `DEFECT-01`은 재현 가능한 실제 결함이다.

| 계층 | 파일 | 현재 선언 | 판정 |
|---|---|---:|---|
| ORM | `backend/app/models/generated.py` | `VECTOR(2048)` | 불일치 |
| 저장 Service | `backend/app/services/admin_ocr.py` | `NEON_VECTOR_DIMENSION = 1024` | 현재 계약 |
| Repository | `backend/app/repositories/document_chunk.py` | `EMBEDDING_COLUMN_WIDTH = 1024` | 현재 계약 |
| 최신 Migration | `backend/migrations/versions/a1f3c9d2e8b4_narrow_chunk_embeddings_to_1024.py` | `NEW_WIDTH = 1024` | 현재 계약 |
| 기본 설정 | `backend/app/core/config.py` | `embedding_dimension = 1024` | 현재 계약 |

---

## 2. 재현 결과

프로젝트 루트에서 다음 단위 계약 테스트를 실행했다.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='.;backend'
.\backend\.venv\Scripts\python.exe -m unittest `
  backend.tests.test_unit_scope_contracts.UnitScopeContractTest.test_chunk_embeddings_orm_width_matches_storage_contract
```

결과:

```text
FAIL: test_chunk_embeddings_orm_width_matches_storage_contract

File "backend/tests/test_unit_scope_contracts.py", line 99
    self.assertEqual(orm_dimension, NEON_VECTOR_DIMENSION)
AssertionError: 2048 != 1024

Ran 1 test in 0.001s
FAILED (failures=1)
```

같은 파일의 테스트 전체를 실행한 결과는 4개 중 해당 계약 테스트 1개만 실패했다.

```text
Ran 4 tests in 0.003s
FAILED (failures=1)
```

테스트는 다음 값을 직접 비교한다.

```python
orm_dimension = ChunkEmbeddings.__table__.c.embedding.type.dim
self.assertEqual(orm_dimension, NEON_VECTOR_DIMENSION)
```

즉 실패값 `2048`은 문자열 검색 결과가 아니라 실행 시점의 실제 SQLAlchemy metadata 값이다.

---

## 3. 코드 근거

### 3.1 ORM은 과거 2048 계약을 유지

`backend/app/models/generated.py`:

```python
class ChunkEmbeddings(Base):
    ...
    # 컬럼 폭은 2048로 넓게 잡고 ...
    embedding: Mapped[Optional[Any]] = mapped_column(VECTOR(2048))
```

ORM 주석도 짧은 Vector를 2048까지 zero-padding한다는 과거 정책을 설명한다. 현재 Repository는 1024까지만 padding하므로 선언뿐 아니라 주석도 현재 동작과 다르다.

### 3.2 저장 Service는 정확히 1024차원을 강제

`backend/app/services/admin_ocr.py`:

```python
NEON_VECTOR_DIMENSION = 1024
```

`_validate_embeddings_before_storage()`는 다음 조건을 저장 전에 검증한다.

- 설정 차원이 정확히 1024인지
- Jina/BGE 두 Provider 결과가 모두 존재하는지
- Chunk 수와 Provider별 Vector 수가 같은지
- 모든 Vector 길이가 정확히 1024인지

1024가 아닌 Vector는 Repository 호출 전에 `EmbeddingValidationError`로 거부된다.

### 3.3 Repository도 1024차원으로 저장·검색

`backend/app/repositories/document_chunk.py`:

```python
EMBEDDING_COLUMN_WIDTH = 1024
```

`pad_embedding()`은 입력 Vector를 1024 길이로 맞춘다. 이 함수는 다음 경로에 공통 적용된다.

- `DocumentChunkRepository.add_embeddings()` 저장
- `DocumentChunkRepository.search_by_provider()` 검색 Query
- `DocumentRepository.save_with_chunks()` 저장
- `DocumentRepository.append_staged_chunks()` 배치 저장

### 3.4 최신 Migration은 DB 컬럼을 1024로 축소

`backend/migrations/versions/a1f3c9d2e8b4_narrow_chunk_embeddings_to_1024.py`:

```python
NEW_WIDTH = 1024
OLD_WIDTH = 2048
```

Upgrade는 기존 Vector의 앞 1024개 값만 유지하며 컬럼 타입을 `vector(1024)`로 바꾼다.

```sql
ALTER TABLE vector_db.chunk_embeddings
ALTER COLUMN embedding TYPE vector(1024)
USING (embedding::real[])[1:1024]::vector(1024)
```

Migration 연결 순서도 정상이다.

```text
03b8a4b5b62a  chunk_embeddings VECTOR(2048) 생성
→ 0dcef89659d1
→ ebf81fbe5350
→ a1f3c9d2e8b4  VECTOR(1024)로 축소
→ d4e6f1a9c3b7
→ 이후 Migration
```

---

## 4. 발생 원인

초기 `03b8a4b5b62a` Migration은 향후 더 큰 Embedding 모델을 고려해 `VECTOR(2048)`로 테이블을 만들었다. 이후 Jina v4와 Medical BGE-M3의 실제 계약이 1024차원으로 확정되면서 `a1f3c9d2e8b4` Migration과 Repository가 1024로 변경됐다.

그러나 이 변경이 `backend/app/models/generated.py`의 `ChunkEmbeddings.embedding` 선언과 관련 주석에는 반영되지 않았다.

Git 이력상 ORM의 2048 선언은 2026-08-28 추가된 상태를 유지하고, Repository의 1024 계약은 2026-09-04 반영됐다. 최신 DB 계약으로 ORM을 다시 생성하거나 동기화하는 절차가 빠진 것이 직접 원인이다.

---

## 5. 런타임 영향 분석

### 5.1 최신 Migration이 적용된 DB

실제 DB 컬럼이 `vector(1024)`이고 Application이 1024개 값을 전달한다면 현재 저장과 검색이 즉시 실패하지 않을 수 있다.

로컬에서 pgvector SQLAlchemy bind processor를 확인한 결과, ORM 타입이 `VECTOR(2048)`이어도 1024개 값 자체는 문자열로 직렬화됐다. 생성된 PostgreSQL INSERT와 cosine-distance SQL에도 Parameter를 `vector(2048)`로 강제하는 명시적 cast는 붙지 않았다.

다만 이것은 ORM metadata가 올바르다는 뜻이 아니다. 최종 차원 검증은 실제 PostgreSQL 컬럼 타입이 담당하므로 DB schema 상태에 따라 결과가 달라진다.

### 5.2 최신 Migration이 적용되지 않은 DB

실제 DB가 아직 `vector(2048)`이면 현재 Repository는 1024개 값만 전송한다. 이 경우 PostgreSQL/pgvector가 컬럼의 기대 차원과 입력 차원이 다르다고 판단해 저장을 거부할 수 있다.

따라서 배포 환경마다 Alembic 적용 상태가 다르면 동일 코드에서 성공과 실패가 갈릴 수 있다.

### 5.3 Alembic autogenerate

`backend/migrations/env.py`는 다음 설정을 사용한다.

```python
target_metadata = Base.metadata
compare_type=True
```

`Base`는 `app.models.generated.Base`다. 따라서 최신 DB가 `vector(1024)`여도 ORM metadata는 `VECTOR(2048)`을 기대한다. 다음 autogenerate에서 DB를 다시 2048로 넓히는 타입 변경이 후보로 생성될 위험이 있다.

### 5.4 신규 환경

저장소에서는 `Base.metadata.create_all()` 호출 경로가 확인되지 않았다. Alembic Migration만 정상 적용하는 신규 환경은 최종적으로 1024가 된다. 하지만 ORM metadata를 직접 사용하는 테스트, schema 도구 또는 별도 초기화 도구는 2048을 기준으로 판단할 수 있다.

---

## 6. 위험도

| 항목 | 위험 | 설명 |
|---|---|---|
| 계약 테스트 | 확인됨 | `AssertionError: 2048 != 1024`로 항상 실패 |
| 현재 저장·검색 | 환경 의존 | 실제 DB가 최신 `vector(1024)`이면 동작 가능성이 높음 |
| Migration 미적용 환경 | 높음 | DB 2048과 Application 1024 입력이 충돌할 수 있음 |
| Alembic autogenerate | 높음 | 1024를 2048로 되돌리는 잘못된 schema 변경 후보 가능 |
| 유지보수 | 중간 | ORM 주석과 Repository 동작이 서로 반대라 회귀 유발 가능 |

종합 판정은 `High`다. 즉시 모든 운영 요청을 중단시키는 장애로 확인되지는 않았지만, schema의 세 기준인 DB Migration·ORM metadata·저장 계약이 일치하지 않아 배포와 후속 Migration에서 위험하다.

---

## 7. 권장 조치

코딩 허가 후 다음 순서로 처리한다.

1. 실제 운영 DB의 Alembic revision을 읽기 전용으로 확인한다.
2. `vector_db.chunk_embeddings.embedding`의 실제 타입이 `vector(1024)`인지 확인한다.
3. 최신 Migration이 적용된 schema를 기준으로 ORM을 재생성하거나, `ChunkEmbeddings.embedding`을 `VECTOR(1024)`로 동기화한다.
4. ORM의 2048 및 zero-padding 설명을 현재 1024 계약에 맞게 갱신한다.
5. 과거 Migration `03b8a4b5b62a`와 축소 Migration `a1f3c9d2e8b4`는 이력 보존을 위해 수정하지 않는다.
6. Alembic autogenerate를 실행해 예상하지 않은 1024→2048 타입 변경이 더 이상 생성되지 않는지 확인한다.
7. 계약 테스트와 저장·검색 회귀 테스트를 실행한다.

`generated.py`가 DB 기반 자동 생성 산출물이라면 단일 줄 수정보다 최신 schema에서 재생성하는 방식을 우선한다. 단, 재생성 결과에 관계·주석 등 수동 보완 내용이 덮어써지지 않는지 diff 검토가 필요하다.

---

## 8. 완료 조건

다음 조건을 모두 만족하면 `DEFECT-01`을 해결 상태로 전환한다.

- `ChunkEmbeddings.__table__.c.embedding.type.dim == 1024`
- `NEON_VECTOR_DIMENSION == 1024`
- `EMBEDDING_COLUMN_WIDTH == 1024`
- 실제 DB의 `vector_db.chunk_embeddings.embedding == vector(1024)`
- `test_chunk_embeddings_orm_width_matches_storage_contract` 통과
- 저장·검색 관련 회귀 테스트 통과
- Alembic autogenerate에 의도하지 않은 Vector 폭 변경 없음
- ORM의 설명과 실제 zero-padding 정책 일치

---

## 9. 조사 범위와 미확인 사항

이번 조사는 다음 작업만 수행했다.

- 관련 ORM, Service, Repository, Migration, Alembic 설정 정적 분석
- SQLAlchemy metadata와 bind processor 로컬 확인
- `backend/tests/test_unit_scope_contracts.py` 실행
- Git 이력과 작업 트리 상태 확인

다음 작업은 수행하지 않았다.

- Production 코드 수정
- Migration 수정 또는 신규 Migration 생성
- 라이브 Neon DB 접속
- Alembic upgrade/downgrade 실행
- 실제 DB INSERT 또는 cosine-distance Query 실행

따라서 운영 DB의 현재 Alembic revision과 실제 컬럼 타입은 별도 읽기 전용 확인이 필요하다.

---

## 10. 관련 파일

| 구분 | 경로 |
|---|---|
| 불일치 ORM | `backend/app/models/generated.py` |
| 저장·검색 Repository | `backend/app/repositories/document_chunk.py` |
| OCR 저장 Repository | `backend/app/repositories/document_repository.py` |
| 저장 전 검증 Service | `backend/app/services/admin_ocr.py` |
| Embedding 기본 설정 | `backend/app/core/config.py` |
| 초기 2048 Migration | `backend/migrations/versions/03b8a4b5b62a_add_chunk_embeddings_table.py` |
| 최신 1024 Migration | `backend/migrations/versions/a1f3c9d2e8b4_narrow_chunk_embeddings_to_1024.py` |
| Alembic metadata 설정 | `backend/migrations/env.py` |
| 계약 테스트 | `backend/tests/test_unit_scope_contracts.py` |

