"""Exceptions de la couche IA.

Volontairement indépendantes de FastAPI : ai/ ne doit jamais lever de
HTTPException. C'est à la couche API de traduire ces erreurs en réponses HTTP.
"""


class LLMError(Exception):
    """Erreur générique de la couche IA."""


class LLMProviderNotConfiguredError(LLMError):
    """Le fournisseur demandé est inconnu ou sa clé API n'est pas configurée."""


class LLMRequestError(LLMError):
    """L'appel au fournisseur LLM a échoué (réseau, quota, réponse invalide...)."""


class EmbeddingError(Exception):
    """Erreur générique de la couche embeddings (RAG, semaine 4)."""


class EmbeddingProviderNotConfiguredError(EmbeddingError):
    """Le fournisseur d'embeddings demandé est inconnu ou sa clé API n'est pas configurée."""


class EmbeddingRequestError(EmbeddingError):
    """L'appel au fournisseur d'embeddings a échoué (réseau, quota, réponse invalide...)."""


__all__ = [
    "EmbeddingError",
    "EmbeddingProviderNotConfiguredError",
    "EmbeddingRequestError",
    "LLMError",
    "LLMProviderNotConfiguredError",
    "LLMRequestError",
]
