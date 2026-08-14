"""Sélection du fournisseur d'embeddings actif.

Seule cette classe connaît la correspondance entre `EMBEDDING_PROVIDER`
(.env) et les classes concrètes de `ai/embeddings/` (miroir de
`ai/providers/factory.py`). Le reste de l'application (EmbeddingService,
services métier) ne manipule que l'interface `EmbeddingProvider` : ajouter un
nouveau fournisseur se limite à créer son module et l'enregistrer ici.
"""
from app.ai.embeddings.base import EmbeddingProvider
from app.ai.embeddings.e5_embedding_provider import E5EmbeddingProvider
from app.ai.embeddings.gemini_embedding_provider import GeminiEmbeddingProvider
from app.ai.embeddings.llama_embedding_provider import LlamaEmbeddingProvider
from app.ai.embeddings.mistral_embedding_provider import MistralEmbeddingProvider
from app.ai.embeddings.openai_embedding_provider import OpenAIEmbeddingProvider
from app.ai.embeddings.qwen_embedding_provider import QwenEmbeddingProvider
from app.ai.exceptions import EmbeddingProviderNotConfiguredError
from app.core.config import settings


class EmbeddingProviderFactory:
    """Instancie le fournisseur d'embeddings configuré via `settings.EMBEDDING_PROVIDER`."""

    _REGISTRY: dict[str, type[EmbeddingProvider]] = {
        "gemini": GeminiEmbeddingProvider,
        "openai": OpenAIEmbeddingProvider,
        "mistral": MistralEmbeddingProvider,
        "qwen": QwenEmbeddingProvider,
        "llama": LlamaEmbeddingProvider,
        "e5": E5EmbeddingProvider,
    }

    @classmethod
    def create(cls, provider_name: str | None = None) -> EmbeddingProvider:
        """Retourne une instance du fournisseur demandé (ou celui configuré par défaut)."""

        name = (provider_name or settings.EMBEDDING_PROVIDER).strip().lower()
        provider_cls = cls._REGISTRY.get(name)

        if provider_cls is None:
            raise EmbeddingProviderNotConfiguredError(
                f"Unknown embedding provider '{name}'. Available: {', '.join(cls._REGISTRY)}"
            )

        return provider_cls()


__all__ = ["EmbeddingProviderFactory"]
