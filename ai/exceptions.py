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


__all__ = ["LLMError", "LLMProviderNotConfiguredError", "LLMRequestError"]
