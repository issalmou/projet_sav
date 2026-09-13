"""Fournisseur d'embeddings E5 (intfloat/multilingual-e5-small, local, sans clé API)."""
import asyncio
import threading
from functools import lru_cache

import torch
from sentence_transformers import SentenceTransformer

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.exceptions import EmbeddingRequestError
from app.core.config import settings

_load_lock = threading.Lock()


@lru_cache(maxsize=None)
def _load_model_cached(model_name: str, device: str) -> SentenceTransformer:
    return SentenceTransformer(model_name, device=device)


def _load_model(model_name: str, device: str) -> SentenceTransformer:
    """Charge les poids une seule fois par processus.

    `E5EmbeddingProvider` est reconstruit à chaque tour de chat (nouveau
    `RetrieverService`/`ChatService` par requête) : sans ce cache, chaque
    message rechargerait le modèle depuis le disque (plusieurs secondes,
    plusieurs centaines de Mo de RAM), même pour un tour qui n'appelle
    jamais `search_docs`. Chaque appel passe par `asyncio.to_thread`
    (thread séparé) : sans le verrou, deux tours concurrents pendant le
    premier chargement (ex. warmup de démarrage + premier message client)
    contourneraient tous les deux le cache encore vide et relanceraient
    chacun un téléchargement complet du modèle en parallèle.
    """

    with _load_lock:
        return _load_model_cached(model_name, device)


class E5EmbeddingProvider(EmbeddingProvider):
    """Fournisseur basé sur sentence-transformers, exécuté localement (GPU si disponible, sinon CPU)."""

    def __init__(self) -> None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = _load_model(settings.E5_EMBEDDING_MODEL, device)

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        try:
            embeddings = await asyncio.to_thread(self._model.encode, texts, convert_to_numpy=True)
        except Exception as exc:  # modèle corrompu, mémoire insuffisante...
            raise EmbeddingRequestError(str(exc)) from exc

        return embeddings.tolist()


__all__ = ["E5EmbeddingProvider"]
