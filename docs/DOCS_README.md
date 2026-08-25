# Agent Documentation Naming & Directory Guide

본 문서는 Code Agent가 `docs/` 디렉토리 내에 Markdown(.md) 문서를 생성하고 관리할 때 준수해야 하는 폴더 구조 및 파일명 명명 규칙(Naming Convention)을 정의합니다.

---

## 1. Directory Structure

모든 문서는 목적에 맞춰 아래의 지정된 하위 폴더에 저장되어야 합니다.

```text
docs/
├── DOCS_README.md               # 본 문서 (Agent 및 관리자용 가이드)
├── 1_prompts/              # 코드 생성을 위한 지시문 및 프롬프트
├── 2_reports/              # 작업 수행 결과 및 보고서
├── 3_flows/                # 시스템 구조, 아키텍처, 기능 흐름도
└── 4_errors/               # 에러 분석, 트러블슈팅, 회고 문서
```

---

## 2. File Naming Convention

문서 파일명은 아래 표준 형식을 정확히 준수하여 작성합니다.

```text
[문서번호]_[TAG]_[대상/기능]_[핵심내용]_[YYYYMMDD].md

```

---

## 3. Format Details

| 항목          | 자릿수 / 형식          | 설명 및 규칙                                            |
| ------------- | ---------------------- | ------------------------------------------------------- |
| **문서번호**  | `00`~`99` (2자리 숫자) | 작업 순서나 관리 번호. `00`부터 시작하여 순차 증가      |
| **TAG**       | 대문자 영문 3자리      | 폴더 구분에 맞춘 식별 태그 (`PRM`, `RPT`, `FLW`, `ERR`) |
| **대상/기능** | 영문/한글 단어         | 작업 대상 모듈 또는 기능명 (예: `OCR`, `Auth`, `User`)  |
| **핵심내용**  | 영문/한글 단어         | 문서의 구체적 주제 (공백 없이 작성)                     |
| **YYYYMMDD**  | 8자리 숫자             | 문서 생성 날짜 (예: `20260820`)                         |

---

## 4. Category TAG Mapping

| Directory    | TAG   | Description                                   |
| ------------ | ----- | --------------------------------------------- |
| `1_prompts/` | `PRM` | 코드 생성 요청 지시문, Prompt Specification   |
| `2_reports/` | `RPT` | 작업 완료 보고, 결과 로그, Task Summary       |
| `3_flows/`   | `FLW` | 시스템 아키텍처, 모듈 간 흐름도, 시퀀스 설명  |
| `4_errors/`  | `ERR` | 에러 원인 분석, 트러블슈팅 가이드, Postmortem |

---

## 5. Examples by Directory

### `1_prompts/` (TAG: PRM)

- `00_PRM_OCR_기능구현_20260820.md`
- `01_PRM_Auth_JWT토큰발급_20260821.md`

### `2_reports/` (TAG: RPT)

- `00_RPT_OCR_구현결과_20260820.md`
- `01_RPT_Database_마이그레이션_20260822.md`

### `3_flows/` (TAG: FLW)

- `00_FLW_OCR_전체구조_20260820.md`
- `01_FLW_Payment_결제승인흐름_20260823.md`

### `4_errors/` (TAG: ERR)

- `00_ERR_OCR_이미지파싱오류_20260820.md`
- `01_ERR_Connection_DB타임아웃_20260824.md`

---

## 6. Instructions for Code Agent

1. **디렉토리 준수**: 문서 성격에 맞춰 지정된 하위 폴더에 저장합니다.
2. **문서번호 관리**: 폴더 내 기존 파일들을 확인하고, 가장 최근 번호 다음 숫자를 2자리(`00`~`99`)로 부여합니다.
3. **구분자 통일**: 언더스코어(`_`)를 구분자로 사용하며 파일명에 공백(Space)을 포함하지 않습니다.
4. **날짜 포맷**: 하이픈 없는 8자리 숫자(`YYYYMMDD`)를 사용합니다.
