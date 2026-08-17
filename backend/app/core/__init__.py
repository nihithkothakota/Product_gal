"""
Application configuration loaded from environment variables.
Uses pydantic-settings for type-safe config with .env file support.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "Product Gallery"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"  # development | staging | production

    # ── API ──────────────────────────────────────────────────────────────
    api_v1_prefix: str = "/v1"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/product_gallery"
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600  # seconds

    # ── JWT ──────────────────────────────────────────────────────────────
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    # ── S3 / MinIO ───────────────────────────────────────────────────────
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "product-gallery"
    s3_region: str = "us-east-1"
    s3_presigned_url_expire: int = 3600  # seconds

    # ── Rate Limiting ────────────────────────────────────────────────────
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_json: bool = True


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
