from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    # 비로그인 사용자도 채팅을 쓸 수 있게 하는 게스트 계정 관련 설정.
    # 게스트 토큰은 로그인 수단이 없으므로 길게 잡아 재방문 시 같은 게스트로 이어지게 한다.
    guest_token_expire_minutes: int = 60 * 24 * 30  # 30일
    guest_daily_message_limit: int = 15

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
