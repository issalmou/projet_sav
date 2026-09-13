"""Service métier du chat IA et des conversations."""
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import SavAgent
from app.ai.embeddings.warmup import warm_embedding_model_in_background
from app.ai.exceptions import LLMError
from app.ai.llm import LLMService
from app.ai.rag.retriever import RetrieverService
from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent
from app.models.message import Message
from app.models.product import Product
from app.models.user import User
from app.schemas.chat import MessageRole
from app.core.permissions import STAFF_ROLES, get_role_name
from app.services.client_product_service import ClientProductService
from app.utils.constants import RoleName

# Un titre de secours reste préférable à un titre vide.
_FALLBACK_TITLE_MAX_LENGTH = 60


class ProductNotAssignedError(Exception):
    """Un client tente d'ouvrir une conversation sur un produit qui ne lui est pas affecté.

    Volontairement PAS une sous-classe de `ValueError` (réservé aux
    « introuvable » → 404) : le produit existe, mais l'accès est refusé → 403.
    """


@dataclass
class ChatTurnResult:
    """Résultat d'un tour de chat : conversation, message assistant, ticket éventuel."""

    conversation: Conversation
    message: Message
    ticket_id: UUID | None = None


class ChatService:
    """Orchestrateur métier pour les conversations, leur historique et l'agent IA."""

    def __init__(
        self,
        session: AsyncSession,
        agent: SavAgent | None = None,
        llm_service: LLMService | None = None,
        retriever: RetrieverService | None = None,
    ) -> None:
        self.session = session
        self._llm_service = llm_service or LLMService()
        self._explicit_agent = agent
        self._explicit_retriever = retriever
        self._lazy_agent: SavAgent | None = None

    @property
    def _agent(self) -> SavAgent:
        """Construit l'agent (et donc le retriever RAG / le modèle d'embeddings) à la
        première utilisation réelle, pas dans `__init__`.

        `ChatService` est instancié pour TOUTES les routes `/chat/*`, y compris
        l'ouverture, la liste, la lecture et la suppression de conversations —
        aucune d'elles n'appelle l'agent. Le construire systématiquement
        chargeait inutilement le modèle E5 / le client ChromaDB sur ces routes,
        alors que seul `handle_message` en a besoin.
        """

        if self._explicit_agent is not None:
            return self._explicit_agent
        if self._lazy_agent is None:
            self._lazy_agent = SavAgent(llm_service=self._llm_service, retriever=self._explicit_retriever)
        return self._lazy_agent

    async def open_conversation(self, user: User, product_id: UUID) -> Conversation:
        """Crée une conversation pour `user` dans le contexte de `product_id` (obligatoire).

        - `product_id` doit référencer un produit existant (`ValueError` → 404) ;
        - si `user` a le rôle « client », le produit doit lui être affecté dans
          `client_products` (`ProductNotAssignedError` → 403). Le staff
          (administrateur / responsable_sav / superuser) n'est pas soumis à
          cette restriction.
        """

        await self._ensure_can_open_conversation(user, product_id)

        conversation = Conversation(user_id=user.id, product_id=product_id)
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        warm_embedding_model_in_background()
        return conversation

    async def get_conversation(
        self, conversation_id: UUID, user: User | UUID, *, allow_staff_access: bool = False
    ) -> Conversation:
        """Retourne la conversation SI elle appartient à `user`, sinon `ValueError` (→ 404).

        C'est LE point de contrôle de propriété : par défaut, un utilisateur ne
        peut jamais lire ni écrire dans la conversation d'un autre, même en
        connaissant son id — `handle_message` et `delete_conversation`
        s'appuient sur cette stricte propriété et ne passent jamais
        `allow_staff_access=True`.

        `allow_staff_access=True` (routes de LECTURE seule, `GET /chat/conversations*`)
        élargit ce périmètre au staff (`STAFF_ROLES`) et au superuser, qui
        voient alors toutes les conversations — jamais pour envoyer un message
        ou en supprimer une à la place du client.
        """

        query = select(Conversation).where(Conversation.id == conversation_id)
        if not (allow_staff_access and isinstance(user, User) and _is_staff_or_superuser(user)):
            user_id = user.id if isinstance(user, User) else user
            query = query.where(Conversation.user_id == user_id)

        result = await self.session.execute(query)
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise ValueError("Conversation not found")
        return conversation

    async def list_conversations(self, user: User) -> list[Conversation]:
        """Liste les conversations visibles par `user` : les siennes, ou toutes
        pour le staff (`STAFF_ROLES`) / un superuser (cf. `get_conversation`)."""

        query = select(Conversation).order_by(Conversation.updated_at.desc())
        if not _is_staff_or_superuser(user):
            query = query.where(Conversation.user_id == user.id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> None:
        conversation = await self.get_conversation(conversation_id, user_id)
        await self.session.delete(conversation)
        await self.session.commit()

    async def add_user_message(self, conversation_id: UUID, content: str) -> Message:
        return await self._add_message(conversation_id, role="user", content=content)

    async def add_assistant_message(self, conversation_id: UUID, content: str) -> Message:
        return await self._add_message(conversation_id, role="assistant", content=content)

    async def get_history(
        self, conversation_id: UUID, user: User | UUID, *, allow_staff_access: bool = False
    ) -> list[Message]:
        await self.get_conversation(conversation_id, user, allow_staff_access=allow_staff_access)
        result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
        )
        return list(result.scalars().all())

    async def _get_diagnostic_events(self, conversation_id: UUID) -> list[ConversationEvent]:
        """Journal du diagnostic (recherche / hypothèses / retours client), chronologique.

        Réinjecté dans le prompt de l'agent (récapitulatif) pour que le
        diagnostic soit réellement multi-tour, et utilisé pour générer la
        description d'un ticket éventuel.
        """

        result = await self.session.execute(
            select(ConversationEvent)
            .where(ConversationEvent.conversation_id == conversation_id)
            .order_by(ConversationEvent.created_at)
        )
        return list(result.scalars().all())

    async def _add_message(self, conversation_id: UUID, *, role: MessageRole, content: str) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def handle_message(self, user: User, conversation_id: UUID, content: str) -> ChatTurnResult:
        """Traite un message dans une conversation EXISTANTE et appartenant à `user`.

        Workflow : vérification de propriété → message client sauvegardé →
        titre (1er/2e message) → agent LangGraph (RAG + outils + escalade) →
        réponse sauvegardée. L'agent peut créer un ticket : `ticket_id` est
        alors renseigné.
        """

        conversation = await self.get_conversation(conversation_id, user.id)

        await self.add_user_message(conversation.id, content)
        history = await self.get_history(conversation.id, user.id)
        events = await self._get_diagnostic_events(conversation.id)
        await self._maybe_update_title(conversation, history, user.preferred_language)

        result = await self._agent.run_turn(
            session=self.session,
            user=user,
            conversation=conversation,
            history=history,
            user_message=content,
            events=events,
        )

        assistant_message = await self.add_assistant_message(conversation.id, result.reply_text)
        await self.session.refresh(conversation)

        return ChatTurnResult(
            conversation=conversation, message=assistant_message, ticket_id=result.created_ticket_id
        )

    async def _ensure_can_open_conversation(self, user: User, product_id: UUID | None) -> None:
        if product_id is None:
            raise ValueError("product_id is required to open a conversation")

        product = await self.session.get(Product, product_id)
        if product is None:
            raise ValueError("Product not found")

        role_name = user.role.name if user.role else None
        if not user.is_superuser and role_name == RoleName.CLIENT.value:
            assigned = await ClientProductService(self.session).is_assigned(user.id, product_id)
            if not assigned:
                raise ProductNotAssignedError("This product is not assigned to your account")

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


def _is_staff_or_superuser(user: User) -> bool:
    """Staff (`STAFF_ROLES` : administrateur / responsable_sav) ou superuser :
    ces comptes voient toutes les conversations en lecture (cf. `get_conversation`)."""

    return user.is_superuser or get_role_name(user) in STAFF_ROLES


def _fallback_title(content: str, *, max_length: int = _FALLBACK_TITLE_MAX_LENGTH) -> str:
    stripped = content.strip()
    if len(stripped) <= max_length:
        return stripped
    truncated = stripped[:max_length].rsplit(" ", 1)[0]
    return f"{truncated}…" if truncated else stripped[:max_length]


__all__ = ["ChatService", "ChatTurnResult", "ProductNotAssignedError"]
