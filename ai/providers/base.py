"""Interface commune à tous les fournisseurs de LLM.

Le reste de l'application (ai/llm.py, ai/agent/, services/chat_service.py) ne
dépend que de ce contrat, jamais d'un SDK concret. C'est ce qui permet de
changer de fournisseur via `.env` (LLM_PROVIDER) sans modifier le reste du
code — y compris pour l'agent LangGraph, qui appelle `agenerate_tools` sur le
provider injecté et n'est donc couplé à aucun fournisseur.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# Un message d'échange. Formes possibles :
#   {"role": "system"|"user"|"assistant", "content": str}
#   {"role": "assistant", "content": str, "tool_calls": [ToolCall-as-dict, ...]}
#   {"role": "tool", "tool_call_id": str, "name": str, "content": str}
Message = dict[str, Any]


@dataclass(frozen=True)
class ToolSpec:
    """Déclaration d'un outil exposé au LLM (nom, description, schéma JSON des paramètres)."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema, type "object"


@dataclass(frozen=True)
class ToolCall:
    """Un appel d'outil demandé par le LLM."""

    id: str
    name: str
    arguments: dict[str, Any]

    def as_message(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}


@dataclass(frozen=True)
class LLMResult:
    """Résultat d'un tour LLM avec outils.

    `tool_calls` vide => `text` est la réponse finale. Sinon, l'appelant doit
    exécuter les outils, ré-injecter leurs résultats et rappeler le LLM.
    """

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)


class LLMProvider(ABC):
    """Contrat minimal que tout fournisseur LLM doit respecter."""

    @abstractmethod
    async def agenerate(self, messages: list[Message], **kwargs: object) -> str:
        """Envoie une liste de messages {"role", "content"} et retourne le texte généré."""
        raise NotImplementedError

    @abstractmethod
    async def agenerate_tools(
        self, messages: list[Message], tools: list[ToolSpec]
    ) -> LLMResult:
        """Envoie l'historique + les outils disponibles et retourne texte OU appels d'outils."""
        raise NotImplementedError


__all__ = ["LLMProvider", "LLMResult", "Message", "ToolCall", "ToolSpec"]
