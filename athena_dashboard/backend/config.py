"""Configuration for FastAPI backend."""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings."""

    # Basic config
    APP_NAME: str = "Athena Monitoring Dashboard"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server config
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./athena.db"
    ATHENA_DB_PATH: str = str(
        Path.home() / ".athena" / "memory.db"
    )  # Athena memory database

    # Athena HTTP API
    ATHENA_HTTP_URL: str = "http://localhost:3000"  # Athena HTTP service
    USE_ATHENA_HTTP: bool = True  # Use HTTP loader instead of direct database access

    # Redis cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 60  # Cache for 60 seconds

    # API config
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
    ]

    # WebSocket config
    WEBSOCKET_ENABLED: bool = True
    WEBSOCKET_CHECK_INTERVAL: int = 5  # Check for updates every 5 seconds

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    # Metrics aggregation
    METRICS_UPDATE_INTERVAL: int = 5  # Seconds
    HISTORY_RETENTION_DAYS: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
