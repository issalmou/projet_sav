"""Service métier du chat IA : conversations, historique et orchestration LLM.

Ce module gère la persistance (créer une conversation, ajouter un message,
lire l'historique) ainsi que le workflow complet d'échange avec l'agent IA :
Utilisateur -> Conversation -> Historique -> Recherche RAG -> Contexte
documentaire -> LLM -> Réponse -> Sauvegarde -> Retour. 
Chaque méthode qui accède à une conversation existante vérifie qu'elle
appartient à `user_id`, pour qu'un utilisateur ne puisse jamais lire ou
modifier les conversations d'un autre.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.exceptions import LLMError
from app.ai.llm import LLMService
from app.ai.memory import ConversationMemory
from app.ai.prompts import LOW_CONFIDENCE_INSTRUCTION, build_context_section, build_system_prompt
from app.ai.rag.retriever import RetrievedChunk, RetrieverService
from app.core.logger import logger
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import MessageRole

# Titre de secours (troncature du 1er message) si la génération LLM échoue :
# on préfère un titre mécanique mais lisible à une conversation sans titre.
_FALLBACK_TITLE_MAX_LENGTH = 60


class ChatService:
    """Orchestrateur métier pour les conversations, leur historique et l'agent IA."""

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService | None = None,
        retriever: RetrieverService | None = None,
    ) -> None:
        self.session = session
        # Injectables pour les tests (LLMService/RetrieverService branchés sur
        # des doubles factices) ; par défaut, résolvent le fournisseur actif
        # via LLM_PROVIDER / EMBEDDING_PROVIDER (.env).
        self._llm_service = llm_service or LLMService()
        self._retriever = retriever or RetrieverService()

    async def create_conversation(self, user_id: UUID, title: str | None = None) -> Conversation:
        """Crée une nouvelle conversation pour `user_id`."""

        conversation = Conversation(user_id=user_id, title=title)
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_conversation(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        """Retourne la conversation si elle appartient à `user_id`, sinon lève ValueError."""

        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()

        if conversation is None:
            raise ValueError("Conversation not found")

        return conversation

    async def list_conversations(self, user_id: UUID) -> list[Conversation]:
        """Liste les conversations de `user_id`, les plus récemment actives d'abord."""

        result = await self.session.execute(
            select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def add_user_message(self, conversation_id: UUID, content: str) -> Message:
        """Ajoute le message d'un utilisateur à une conversation."""

        return await self._add_message(conversation_id, role="user", content=content)

    async def add_assistant_message(self, conversation_id: UUID, content: str) -> Message:
        """Ajoute la réponse de l'agent IA à une conversation."""

        return await self._add_message(conversation_id, role="assistant", content=content)

    async def get_history(self, conversation_id: UUID, user_id: UUID) -> list[Message]:
        """Retourne l'historique ordonné d'une conversation appartenant à `user_id`."""

        await self.get_conversation(conversation_id, user_id)

        result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
        )
        return list(result.scalars().all())

    async def _add_message(self, conversation_id: UUID, *, role: MessageRole, content: str) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def send_message(
        self,
        user: User,
        content: str,
        conversation_id: UUID | None = None,
        product_id: UUID | None = None,
        extra_system_instructions: str | None = None,
    ) -> tuple[Conversation, Message]:
        """Traite un message utilisateur et retourne (conversation, réponse de l'agent IA).

        Workflow : conversation (récupérée ou créée) -> message utilisateur
        sauvegardé -> historique -> recherche RAG (filtrée par `product_id`
        si connu, sinon globale) -> contexte documentaire injecté dans le
        prompt système -> appel LLM -> réponse sauvegardée -> retour.

        `extra_system_instructions`, si fourni, est ajouté à la fin du prompt
        système (ex: instruction de statut du diagnostic automatique, cf.
        `DiagnosticService`), sans changer le workflow du chat classique.
        """

        if conversation_id is None:
            conversation = await self.create_conversation(user.id)
        else:
            conversation = await self.get_conversation(conversation_id, user.id)

        await self.add_user_message(conversation.id, content)

        history = await self.get_history(conversation.id, user.id)
        await self._maybe_update_title(conversation, history, user.preferred_language)

        retrieved_chunks = await self._retrieve_context(content, product_id)

        system_prompt = build_system_prompt(user.preferred_language) + build_context_section(retrieved_chunks)
        if product_id is None and RetrieverService.is_low_confidence(retrieved_chunks):
            system_prompt += LOW_CONFIDENCE_INSTRUCTION
        if extra_system_instructions:
            system_prompt += extra_system_instructions

        llm_messages = [
            {"role": "system", "content": system_prompt},
            *ConversationMemory.to_llm_messages(history),
        ]

        reply_text = await self._llm_service.generate_reply(llm_messages)
        assistant_message = await self.add_assistant_message(conversation.id, reply_text)

        return conversation, assistant_message

    async def _retrieve_context(self, content: str, product_id: UUID | None) -> list[RetrievedChunk]:
        """Interroge le RAG pour `content`, sans jamais faire échouer le chat en cas de souci.

        Contrairement au LLM (indispensable au chat), le RAG est une couche
        d'enrichissement : si la recherche échoue (ex: ChromaDB indisponible,
        quota d'embeddings épuisé), l'agent doit pouvoir répondre quand même,
        sans contexte documentaire, plutôt que de renvoyer une erreur au client.
        """

        try:
            return await self._retriever.retrieve(content, product_id=product_id)
        except Exception:
            logger.warning("RAG retrieval failed, answering without documentary context", exc_info=True)
            return []

    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> None:
        """Supprime une conversation (et son historique, par cascade DB) appartenant à `user_id`."""

        conversation = await self.get_conversation(conversation_id, user_id)
        await self.session.delete(conversation)
        await self.session.commit()

    async def _maybe_update_title(
        self, conversation: Conversation, history: list[Message], preferred_language: str
    ) -> None:
        """Génère le titre après la 1re question, l'affine après la 2e, puis ne le touche plus."""

        user_messages = [message.content for message in history if message.role == "user"]

        if len(user_messages) == 1:
            content_for_title = user_messages[0]
        elif len(user_messages) == 2:
            content_for_title = f"{user_messages[0]} {user_messages[1]}"
        else:
            return

        try:
            title = await self._llm_service.generate_title(content_for_title, preferred_language)
        except LLMError:
            title = _fallback_title(content_for_title)

        conversation.title = title
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)


def _fallback_title(content: str, *, max_length: int = _FALLBACK_TITLE_MAX_LENGTH) -> str:
    """Titre de secours : le message tronqué au dernier mot entier, sans le couper en plein milieu."""

    stripped = content.strip()

    if len(stripped) <= max_length:
        return stripped

    truncated = stripped[:max_length].rsplit(" ", 1)[0]
    return f"{truncated}…" if truncated else stripped[:max_length]


__all__ = ["ChatService"]
