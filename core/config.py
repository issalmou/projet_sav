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
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 jours
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # --- Base de données ---
    DATABASE_URL: str = Field(..., description="DSN PostgreSQL au format postgresql+asyncpg://...")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # --- IA / Intégrations ---
    # Fournisseur actif, choisi automatiquement à partir de cette variable
    # (cf. app.ai.providers.factory.LLMProviderFactory). Valeurs possibles :
    # "gemini", "openai", "mistral", "qwen", "llama".
    LLM_PROVIDER: str = "gemini"

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    MISTRAL_API_KEY: str | None = None
    MISTRAL_MODEL: str = "mistral-small-latest"

    # Qwen (Alibaba Cloud DashScope) expose une API compatible OpenAI.
    QWEN_API_KEY: str | None = None
    QWEN_MODEL: str = "qwen-plus"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Llama : servi via une API compatible OpenAI (Ollama en local par défaut,
    # ou tout endpoint compatible tel que Groq/Together en changeant l'URL).
    LLAMA_API_KEY: str | None = None
    LLAMA_MODEL: str = "llama3.1"
    LLAMA_BASE_URL: str = "http://localhost:11434/v1"

    # --- Embeddings (RAG)---
    # Fournisseur indépendant de LLM_PROVIDER (cf. app.ai.embeddings.factory) :
    # un provider peut servir le chat sans faire d'embeddings performants, et
    # inversement. Valeurs possibles : "gemini", "openai", "mistral", "qwen",
    # "llama". Réutilise les clés API / URLs déjà définies ci-dessus.
    EMBEDDING_PROVIDER: str = "gemini"

    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    MISTRAL_EMBEDDING_MODEL: str = "mistral-embed"
    QWEN_EMBEDDING_MODEL: str = "text-embedding-v3"
    # Modèle Ollama dédié à l'embedding (distinct du modèle de chat LLAMA_MODEL).
    LLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    # E5 : modèle local (sentence-transformers), gratuit, sans clé API.
    E5_EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"

    # --- Bootstrap (compte super admin initial, utilisé par database/seed.py) ---
    FIRST_ADMIN_EMAIL: str | None = None
    FIRST_ADMIN_PASSWORD: str | None = None

    # --- Journalisation ---
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # --- Multilingue ---
    DEFAULT_LANGUAGE: str = "fr"
    SUPPORTED_LANGUAGES: str = "fr,en,ar"

    # --- Documents (base de connaissances / RAG) ---
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    # --- Vector Database (RAG) ---
    CHROMA_DB_DIR: Path = BASE_DIR / "chroma_db"

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