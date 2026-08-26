# ai/ocr — Framework 독립 문서 OCR Core

## 중심 흐름

```text
analyze_document(OcrDocumentInput, OcrProcessingConfig)
→ validation.validate_document()
→ Image / PDF / DOCX / PPTX 형식별 추출
→ 공통 Image 전처리
→ 단일 PaddleOcrService
→ Raw Text 보존과 Cleaned Text 생성
→ OcrDocumentResult 반환
```

`pipeline.py`의 `analyze_document()`가 전체 실행 순서를 관리한다. PDF와 Office 추출기는 세부 작업 결과를 `ExtractedDocument`로 이 함수에 반환하며, Chunking·HTTP Response·Job·DB 저장은 수행하지 않는다.

## PaddleOCR Engine

`engine.py`만 `PaddleOCR`를 생성하고 `predict()`를 호출한다.

- 기준 버전: `paddlepaddle>=3.3,<3.4`, `paddleocr>=3.7,<3.8`
- 모델: `PP-OCRv5`, `lang="korean"`
- `use_doc_orientation_classify=False`
- `use_doc_unwarping=False`
- `use_textline_orientation=False`
- `enable_mkldnn=False`
- 설정별 지연 로딩·Cache, 초기화 Lock, 추론 Lock 유지
- GPU 초기화 실패 시 CPU Fallback 유지

실제 모델은 첫 Image OCR 요청에서 준비될 수 있다. Import나 Unit Test만으로 모델을 Download하지 않는다.

## 전처리

`preprocessing.py`의 순서는 다음과 같다.

```text
Image Decode → EXIF 방향 → 투명 배경 흰색 합성 → 한 번 Resize
→ Option이 켜진 경우 Denoise → Deskew → RGB PIL Image
```

PDF Rendering Image, Office 포함 Image, 일반 Image가 모두 같은 함수를 사용한다. Denoise와 Deskew는 `OcrProcessingConfig`로 명시하며 Backend 환경변수 `OCR_ENABLE_DENOISE`, `OCR_ENABLE_DESKEW`가 값을 조립한다.

## 결과 계약

- `raw_text`: Confidence 필터와 공통 Text 정제 전 원문
- `cleaned_text`: 제어문자·과도한 빈 줄을 정리한 Text
- `lines`: 실제 OCR Line의 Text·Confidence·Page·Box·Source
- Native PDF 및 Office 직접 추출 Text는 실제 OCR Line으로 위장하지 않는다.

기존 외부 호출자를 위해 다음 Import는 유지한다.

```python
from ai.ocr import run_ocr
```

`run_ocr()`는 별도 Engine을 만들지 않고 `analyze_document()`를 호출하는 호환 Wrapper다.

## 의존 방향

```text
Backend / Worker / Local Lab → ai/ocr
ai/ocr ─X→ fastapi, app.*, sqlalchemy
```

## Test

프로젝트 최상위에서 실행한다.

```powershell
backend\.venv\Scripts\python.exe -B -m unittest discover -s tests -t . -p "test_*.py" -v
```

실제 Paddle Model Smoke Test는 Unit Test와 분리하고, 실행하지 않았다면 통과했다고 기록하지 않는다.
