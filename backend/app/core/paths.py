"""실행 위치와 무관하게 사용하는 프로젝트 공통 경로를 정의합니다."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT_ENV_FILE = PROJECT_ROOT / ".env"
