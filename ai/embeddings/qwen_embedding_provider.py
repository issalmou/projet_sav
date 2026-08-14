"""Fournisseur d'embeddings Qwen (Alibaba Cloud DashScope, API compatible OpenAI)."""
from app.ai.embeddings._openai_compatible import OpenAICompatibleEmbeddingProvider
from app.ai.exceptions import EmbeddingProviderNotConfiguredError
from app.core.config import settings


class QwenEmbeddingProvider(OpenAICompatibleEmbeddingProvider):
    """Fournisseur Qwen via l'endpoint "compatible-mode" de DashScope."""

    def __init__(self) -> None:
        if not settings.QWEN_API_KEY:
            raise EmbeddingProviderNotConfiguredError("QWEN_API_KEY is not configured")

        super().__init__(
            api_key=settings.QWEN_API_KEY, model=settings.QWEN_EMBEDDING_MODEL, base_url=settings.QWEN_BASE_URL
        )


__all__ = ["QwenEmbeddingProvider"]
