# ai/ocr — 문서/이미지 텍스트 추출

## 엔진
PaddleOCR (`lang="korean"`, `use_angle_cls=True`). 무거운 모델이라 `_get_engine()`에서
지연 로딩 + 캐싱한다 — 모듈을 import만 해도 모델이 안 뜨고, 첫 `run_ocr()` 호출 때 로드된다.

## 흐름
```
run_ocr(image_bytes) → preprocessing.preprocess() → PaddleOCR → postprocessing.postprocess() → OcrResult
```
- **전처리** (`preprocessing.py`): 노이즈 제거(`fastNlMeansDenoisingColored`) → 기울기 보정(`deskew`,
  0.3도 미만이면 안 건드림). 대비 보정/이진화는 PaddleOCR 자체 전처리와 겹쳐 정확도가
  떨어지는 경우가 있어 일부러 안 넣었다 — 필요해지면 실제 문서로 A/B 테스트 후 추가할 것.
- **후처리** (`postprocessing.py`): `min_confidence`(기본 0.5) 미만인 라인은 버리고,
  중복 공백/개행만 정리한다.

## 반환값
`OcrResult(text: str, lines: list[OcrLine], min_confidence: float)` — `lines`는 라인별
원문+신뢰도를 그대로 들고 있어서, 화면에 "신뢰도 낮아서 버려진 부분"을 보여주거나
`min_confidence`를 바꿔가며 재현할 때 씀.

## 절대 금지 (루트 CLAUDE.md에서 이어짐)
- **원본 OCR 텍스트 덮어쓰기 금지** — 사용자가 파싱 결과를 수정하더라도 원본 `OcrResult.text`는
  별도로 보존해야 한다 (DB에 저장할 때 원본/수정본 컬럼을 분리할 것).
- API 키 하드코딩 금지, 확인 없는 대규모 리팩터링 금지는 루트 규칙 그대로 적용.

## 재사용
`backend/app/api/documents`(실제 서비스)와 `backend/local_lab`(로컬 성능테스트, git 미포함)
양쪽에서 이 패키지를 그대로 호출한다. OCR 로직 자체는 여기 한 곳에만 있어야 한다 — 호출하는
쪽(backend API, local_lab, 나중엔 admin 비교 도구)마다 따로 구현하지 말 것.
