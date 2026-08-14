"""Fournisseur d'embeddings Mistral AI."""
from mistralai.client import Mistral

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.exceptions import EmbeddingProviderNotConfiguredError, EmbeddingRequestError
from app.core.config import settings


class MistralEmbeddingProvider(EmbeddingProvider):
    """Fournisseur basé sur le SDK officiel `mistralai`."""

    def __init__(self) -> None:
        if not settings.MISTRAL_API_KEY:
            raise EmbeddingProviderNotConfiguredError("MISTRAL_API_KEY is not configured")

        self._client = Mistral(api_key=settings.MISTRAL_API_KEY)
        self._model = settings.MISTRAL_EMBEDDING_MODEL

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._client.embeddings.create_async(model=self._model, inputs=texts)
        except Exception as exc:
            raise EmbeddingRequestError(str(exc)) from exc

        return [item.embedding or [] for item in response.data]


__all__ = ["MistralEmbeddingProvider"]
