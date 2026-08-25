from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MediSense API"
    app_env: str = "local"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: str = "sqlite:///./local.db"
    model_schemas: str = "app_db,vector_db"
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    password_reset_expire_minutes: int = 30
    frontend_url: str = "http://localhost:5173"
    # 비로그인 사용자도 채팅을 쓸 수 있게 하는 게스트 계정 관련 설정.
    # 게스트 토큰은 로그인 수단이 없으므로 길게 잡아 재방문 시 같은 게스트로 이어지게 한다.
    # 아래 두 한도는 하루 단위가 아니라 게스트 계정 하나가 평생 쓸 수 있는 총량이다
    # (다 쓰면 로그인 유도) — 새 게스트를 발급받으면(=localStorage 초기화) 다시 리셋됨.
    guest_token_expire_minutes: int = 60 * 24 * 30  # 30일
    guest_message_limit: int = 30
    guest_attachment_limit: int = 5

    # Hybrid OCR(csj-ocr 브랜치에서 이식) 설정 — 이미지/PDF/Office 문서 처리 한도.
    ocr_max_file_size_mb: int = 20
    ocr_max_pdf_pages: int = 50
    ocr_native_text_min_chars: int = 20
    ocr_significant_image_area_ratio: float = 0.03
    ocr_pdf_render_dpi: int = 200
    ocr_max_image_side: int = 2400
    ocr_max_image_pixels: int = 40_000_000
    ocr_paddle_device: str = "cpu"
    ocr_paddle_language: str = "korean"
    ocr_max_office_uncompressed_size_mb: int = 200
    ocr_max_office_archive_entries: int = 5_000

    # ai/llm(MedGemma LoRA 어댑터 호출)용 — private HF Hub repo 읽기 권한 필요.
    hf_token: str | None = None

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
