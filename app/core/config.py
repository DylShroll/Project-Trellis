from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # DATABASE_URL and database_url both resolve
    )

    app_env: str = "development"

    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    # Short-lived access tokens reduce exposure window if a token is intercepted
    access_token_expire_minutes: int = 15
    # Refresh tokens are longer-lived and stored server-side in Redis for revocation
    refresh_token_expire_days: int = 7

    database_url: str = "postgresql+asyncpg://trellis:trellis@localhost:5432/trellis"
    # db0=app cache, db1=celery broker, db2=celery results — kept separate to avoid key collisions
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "trellis-media-dev"

    # Injected at runtime by the container; empty string means Claude calls will fail gracefully
    anthropic_api_key: str = ""

    # Must be a JSON array in .env (pydantic-settings parses it automatically)
    # e.g. ALLOWED_ORIGINS=["http://localhost:8000","https://app.example.com"]
    allowed_origins: list[str] = ["http://localhost:8000"]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    # lru_cache ensures .env is only read once per process; call get_settings.cache_clear() in tests
    return Settings()
