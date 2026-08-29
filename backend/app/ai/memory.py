"""Mémoire conversationnelle : met en forme l'historique pour le LLM.

Volontairement séparé de `ChatService` : ce module ne fait que transformer des
`Message` déjà persistés en messages {role, content} exploitables par
`LLMService`, sans connaître FastAPI ni la logique métier.
"""
from app.ai.providers.base import Message as LLMMessage
from app.models.message import Message

# Nombre de messages (user + assistant confondus) conservés dans le contexte
# envoyé au LLM, pour éviter un historique illimité (coût, latence, limite de
# tokens).
MAX_HISTORY_MESSAGES = 20


class ConversationMemory:
    """Transforme l'historique d'une conversation en messages exploitables par un LLM."""

    @staticmethod
    def to_llm_messages(history: list[Message]) -> list[LLMMessage]:
        """Convertit les `MAX_HISTORY_MESSAGES` derniers messages au format {role, content}."""

        recent = history[-MAX_HISTORY_MESSAGES:]
        return [{"role": message.role, "content": message.content} for message in recent]


__all__ = ["ConversationMemory", "MAX_HISTORY_MESSAGES"]
