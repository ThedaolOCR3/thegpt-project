"""질병관리청(KDCA) 공공데이터 OpenAPI 60여개를 호출해서, HF 데이터셋과 동일하게
정제/청킹/(선택)벡터화까지 로컬 파일로 준비한다. `scripts/rag_prepare_dataset.py`와
정확히 같은 원칙 - 실제 Neon 저장은 이 스크립트가 하지 않는다.

지금은 골격만 있다 - 실제 60개 엔드포인트 목록과 서비스키가 아직 없다(추측으로
만들지 않음). `data/kdca_endpoints.yaml`(예시: kdca_endpoints.example.yaml)에
실제 엔드포인트가 등록되면, `bruno/KDCA-OpenAPI/`에서 먼저 실제 응답 형태를 눈으로
확인한 뒤(각 API마다 스키마가 다를 수 있음 - HF 데이터셋 때와 동일하게 STEP 0
없이 추측으로 normalize 함수를 만들지 않는다), 이 스크립트로 실제 fetch를 진행한다.

사용법(엔드포인트 등록 후):
    python scripts/kdca_openapi_ingest.py --list                       # 등록된 엔드포인트 목록만 확인
    python scripts/kdca_openapi_ingest.py --source example-endpoint --dry-run  # 실제 호출 없이 registry 검증만
    python scripts/kdca_openapi_ingest.py --source example-endpoint --limit 5  # 실제로 소량만 호출해서 응답 확인

전체 60개를 한 번에 자동으로 부르지 않는다 - 반드시 --source로 하나씩, 사용자가
Bruno로 먼저 확인한 것부터 순서대로 진행한다("체크 후 별도 지시" 원칙).
"""
import argparse
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PROJECT_ROOT / "data" / "kdca_endpoints.yaml"
REGISTRY_EXAMPLE_PATH = PROJECT_ROOT / "data" / "kdca_endpoints.example.yaml"


def load_registry() -> list[dict[str, Any]]:
    path = REGISTRY_PATH if REGISTRY_PATH.exists() else REGISTRY_EXAMPLE_PATH
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("endpoints", [])


def find_endpoint(name: str, registry: list[dict[str, Any]]) -> dict[str, Any] | None:
    for entry in registry:
        if entry.get("name") == name:
            return entry
    return None


def fetch_sample(entry: dict[str, Any], *, service_key: str, num_rows: int) -> httpx.Response:
    """등록된 엔드포인트 하나를 실제로 한 번 호출해서 원본 응답을 그대로 돌려준다.
    normalize/clean/chunk는 여기서 하지 않는다 - 실제 60개마다 응답 스키마가 다를
    가능성이 높아서, 실제 응답을 먼저 눈으로 본 뒤에 데이터셋 어댑터와 같은 방식으로
    추가해야 한다(ai/rag/ingestion/adapters/ 참고)."""
    url = f"{entry['base_url'].rstrip('/')}/{entry['operation'].lstrip('/')}"
    params = {
        "serviceKey": service_key,
        "pageNo": 1,
        "numOfRows": num_rows,
        "type": entry.get("response_type", "json"),
    }
    with httpx.Client(timeout=30.0) as client:
        return client.get(url, params=params)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KDCA OpenAPI 등록/확인용 CLI (실제 대량 fetch는 아직 없음)")
    parser.add_argument("--list", action="store_true", help="registry에 등록된 엔드포인트 이름만 출력")
    parser.add_argument("--source", help="registry에 등록된 엔드포인트 이름 하나")
    parser.add_argument("--service-key", help="발급받은 서비스키 (없으면 KDCA_SERVICE_KEY 환경변수 사용)")
    parser.add_argument("--limit", type=int, default=5, help="샘플 확인용 요청 개수")
    parser.add_argument("--dry-run", action="store_true", help="실제 호출 없이 registry 항목만 검증")
    args = parser.parse_args(argv)

    registry = load_registry()

    if args.list or not args.source:
        print(f"등록된 엔드포인트 {len(registry)}개 (registry: {REGISTRY_PATH.name if REGISTRY_PATH.exists() else REGISTRY_EXAMPLE_PATH.name + ' - 예시만 있음, 실제 파일 아직 없음'}):")
        for entry in registry:
            print(f"  - {entry.get('name')}: {entry.get('description', '(설명 없음)')}")
        if not args.source:
            return 0

    entry = find_endpoint(args.source, registry)
    if entry is None:
        print(f"FAILED: registry에 '{args.source}'가 없습니다. --list로 등록된 이름을 확인하세요.")
        return 1

    if args.dry_run:
        print(f"OK (dry-run): {entry}")
        return 0

    import os

    service_key = args.service_key or os.environ.get("KDCA_SERVICE_KEY")
    if not service_key:
        print("FAILED: --service-key 또는 환경변수 KDCA_SERVICE_KEY가 필요합니다.")
        return 1

    response = fetch_sample(entry, service_key=service_key, num_rows=args.limit)
    print(f"status: {response.status_code}")
    print(response.text[:2000])
    return 0 if response.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
