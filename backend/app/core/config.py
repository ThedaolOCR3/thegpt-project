from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import ROOT_ENV_FILE


class Settings(BaseSettings):
    app_name: str = "Medical AI API"
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
    ocr_job_ttl_minutes: int = 60
    ocr_max_pending_jobs: int = 5
    llm_ollama_enabled: bool = True
    llm_ollama_base_url: str = "http://127.0.0.1:11434"
    llm_ollama_model: str = "gemma3:1b"
    llm_ollama_timeout_seconds: float = 120.0
    llm_ollama_max_concurrency: int = 1
    llm_gemini_enabled: bool = True
    gemini_api_key: str | None = None
    llm_gemini_model: str = "gemini-3.5-flash-lite"
    llm_gemini_timeout_seconds: float = 60.0
    llm_gemini_max_concurrency: int = 2

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
