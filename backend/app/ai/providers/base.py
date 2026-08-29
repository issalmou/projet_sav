"""Interface commune à tous les fournisseurs de LLM.

Le reste de l'application (ai/llm.py, services/chat_service.py) ne dépend
que de ce contrat, jamais d'un SDK concret. C'est ce qui permet de changer
de fournisseur via `.env` (LLM_PROVIDER) sans modifier le reste du code.
"""
from abc import ABC, abstractmethod


Message = dict[str, str]


class LLMProvider(ABC):
    """Contrat minimal que tout fournisseur LLM doit respecter."""

    @abstractmethod
    async def agenerate(self, messages: list[Message], **kwargs: object) -> str:
        """Envoie une liste de messages {"role", "content"} et retourne le texte généré."""
        raise NotImplementedError


__all__ = ["LLMProvider", "Message"]
