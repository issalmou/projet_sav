"""Fournisseur d'embeddings Google Gemini (fournisseur actif par défaut, cf. .env EMBEDDING_PROVIDER)."""
from google import genai

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.exceptions import EmbeddingProviderNotConfiguredError, EmbeddingRequestError
from app.core.config import settings


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Fournisseur basé sur le SDK officiel `google-genai`."""

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise EmbeddingProviderNotConfiguredError("GEMINI_API_KEY is not configured")

        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_EMBEDDING_MODEL

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._client.aio.models.embed_content(model=self._model, contents=texts)
        except Exception as exc:  # erreurs réseau, quota, clé invalide...
            raise EmbeddingRequestError(str(exc)) from exc

        return [embedding.values or [] for embedding in response.embeddings or []]


__all__ = ["GeminiEmbeddingProvider"]
