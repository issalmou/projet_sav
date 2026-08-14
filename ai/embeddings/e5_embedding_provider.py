"""Fournisseur d'embeddings E5 (intfloat/multilingual-e5-small, local, sans clé API)."""
import asyncio

import torch
from sentence_transformers import SentenceTransformer

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.exceptions import EmbeddingRequestError
from app.core.config import settings


class E5EmbeddingProvider(EmbeddingProvider):
    """Fournisseur basé sur sentence-transformers, exécuté localement (GPU si disponible, sinon CPU)."""

    def __init__(self) -> None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = SentenceTransformer(settings.E5_EMBEDDING_MODEL, device=device)

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        try:
            embeddings = await asyncio.to_thread(self._model.encode, texts, convert_to_numpy=True)
        except Exception as exc:  # modèle corrompu, mémoire insuffisante...
            raise EmbeddingRequestError(str(exc)) from exc

        return embeddings.tolist()


__all__ = ["E5EmbeddingProvider"]
