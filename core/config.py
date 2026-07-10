"""Configuration centralisée de l'application.

Les paramètres sensibles sont chargés depuis l'environnement afin de
respecter les exigences de sécurité et de préparation production.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Plateforme IA SAV & Support Technique"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    APP_VERSION: str = "0.1.0"

    # --- Sécurité ---
    SECRET_KEY: str = Field(..., description="Clé secrète utilisée pour signer les tokens JWT")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # --- Base de données ---
    DATABASE_URL: str = Field(..., description="DSN PostgreSQL au format postgresql+asyncpg://...")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # --- IA / Intégrations ---
    OPENAI_API_KEY: str | None = None

    # --- Journalisation ---
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # --- Multilingue ---
    DEFAULT_LANGUAGE: str = "fr"
    SUPPORTED_LANGUAGES: str = "fr,en,ar"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("DATABASE_URL must be a string")

        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)

        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)

        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def supported_languages(self) -> list[str]:
        return [lang.strip() for lang in self.SUPPORTED_LANGUAGES.split(",") if lang.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Settings mis en cache (lu une seule fois par process) pour la performance."""
    return Settings()


settings = get_settings()