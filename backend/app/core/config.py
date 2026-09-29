"""
Typed application configuration management using Pydantic Settings.
Loads and validates settings from environment variables and .env file.
"""

from functools import lru_cache
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global system configuration settings."""

    # Project metadata
    PROJECT_NAME: str = "UdyamSetu AI"
    TAGLINE: str = "Intelligent Industrial Approval & Compliance Platform"
    PROBLEM_STATEMENT: str = "SIH26130"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./udyamsetu.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Security & Auth
    SECRET_KEY: str = "dev-insecure-secret-key-32-chars-long-udyamsetu"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    # AI & LLM Provider
    AI_PROVIDER: str = "mock"  # "mock" | "gemini" | "openai"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-004"

    # Document OCR Intelligence
    OCR_ENGINE: str = "mock"  # "mock" | "tesseract" | "paddleocr"
    TESSERACT_CMD: str = ""

    # Redis Cache & Background Queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    STORAGE_TYPE: str = "local"  # "local" | "s3"
    LOCAL_STORAGE_DIR: str = "./uploads"
    S3_BUCKET: str = "udyamsetu-documents"
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()


settings = get_settings()
