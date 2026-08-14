"""Interface commune à tous les fournisseurs d'embeddings.

Miroir de `ai/providers/base.py` : le reste de l'application (EmbeddingService,
services métier) ne dépend que de ce contrat, jamais d'un SDK concret. C'est
ce qui permet de changer de fournisseur via `.env` (EMBEDDING_PROVIDER) sans
modifier le reste du code.
"""
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Contrat minimal que tout fournisseur d'embeddings doit respecter."""

    @abstractmethod
    async def aembed(self, texts: list[str]) -> list[list[float]]:
        """Retourne un vecteur d'embedding par texte d'entrée, dans le même ordre."""
        raise NotImplementedError


__all__ = ["EmbeddingProvider"]
