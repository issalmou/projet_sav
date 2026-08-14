"""Fournisseur d'embeddings Llama, servi via une API compatible OpenAI.

Par défaut pointe vers un serveur Ollama local (`LLAMA_BASE_URL`), avec un
modèle dédié à l'embedding (`LLAMA_EMBEDDING_MODEL`) distinct du modèle de
chat (`LLAMA_MODEL`) — un modèle de génération de texte n'est pas un modèle
d'embedding.
"""
from app.ai.embeddings._openai_compatible import OpenAICompatibleEmbeddingProvider
from app.ai.exceptions import EmbeddingProviderNotConfiguredError
from app.core.config import settings


class LlamaEmbeddingProvider(OpenAICompatibleEmbeddingProvider):
    """Fournisseur Llama via un endpoint compatible OpenAI (Ollama par défaut)."""

    def __init__(self) -> None:
        if not settings.LLAMA_BASE_URL:
            raise EmbeddingProviderNotConfiguredError("LLAMA_BASE_URL is not configured")

        # Un serveur local (Ollama) n'exige pas de vraie clé, mais le SDK OpenAI
        # requiert une valeur non vide.
        api_key = settings.LLAMA_API_KEY or "not-needed"

        super().__init__(api_key=api_key, model=settings.LLAMA_EMBEDDING_MODEL, base_url=settings.LLAMA_BASE_URL)


__all__ = ["LlamaEmbeddingProvider"]
