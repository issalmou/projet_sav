"""Service Embeddings : point d'entrée unique de la couche embeddings pour le reste de l'app."""
from app.ai.embeddings.base import EmbeddingProvider
from app.ai.embeddings.factory import EmbeddingProviderFactory
from app.ai.exceptions import EmbeddingError


class EmbeddingService:
    """Calcule des embeddings via le fournisseur actif."""

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        # `provider` est injectable pour les tests (fournisseur factice) ;
        # par défaut, le fournisseur actif est résolu via EMBEDDING_PROVIDER (.env).
        self._provider = provider or EmbeddingProviderFactory.create()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Retourne un vecteur d'embedding par texte de `texts`, dans le même ordre."""

        if not texts:
            raise EmbeddingError("Cannot embed an empty list of texts")

        return await self._provider.aembed(texts)


__all__ = ["EmbeddingService"]
