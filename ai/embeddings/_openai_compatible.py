"""Base commune aux fournisseurs d'embeddings exposant une API compatible OpenAI.

OpenAI, Qwen (DashScope) et Llama (Ollama ou tout endpoint compatible)
partagent le même format d'appel "embeddings" : cette classe évite de
dupliquer cette logique dans chacun des trois providers (miroir de
`ai/providers/_openai_compatible.py`).
"""
from openai import AsyncOpenAI

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.exceptions import EmbeddingRequestError


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Fournisseur générique pour toute API compatible OpenAI embeddings."""

    def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._client.embeddings.create(input=texts, model=self._model)
        except Exception as exc:  # erreurs réseau, quota, clé invalide...
            raise EmbeddingRequestError(str(exc)) from exc

        return [item.embedding for item in response.data]


__all__ = ["OpenAICompatibleEmbeddingProvider"]
