"""Fournisseur d'embeddings OpenAI."""
from app.ai.embeddings._openai_compatible import OpenAICompatibleEmbeddingProvider
from app.ai.exceptions import EmbeddingProviderNotConfiguredError
from app.core.config import settings


class OpenAIEmbeddingProvider(OpenAICompatibleEmbeddingProvider):
    """Fournisseur basé sur le SDK officiel `openai`."""

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise EmbeddingProviderNotConfiguredError("OPENAI_API_KEY is not configured")

        super().__init__(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_EMBEDDING_MODEL)


__all__ = ["OpenAIEmbeddingProvider"]
