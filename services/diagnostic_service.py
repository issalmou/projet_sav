"""Service de diagnostic automatique (CDC semaine 5).

Réutilise ChatService (conversation, historique, RAG, LLM) sans dupliquer sa
logique : ce service ajoute uniquement l'instruction de statut de diagnostic
au prompt système via `extra_system_instructions`, puis interprète le statut
que le LLM a renvoyé. Sur escalade (tâche 7), délègue la création/recherche
de ticket à TicketService, sans dupliquer sa logique d'accès ni de
dédoublonnage.
"""
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMService
from app.ai.prompts import DIAGNOSTIC_STATUS_INSTRUCTION, DIAGNOSTIC_STATUS_MARKERS
from app.ai.rag.retriever import RetrieverService
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketAutoCreate
from app.services.chat_service import ChatService
from app.services.ticket_service import TicketService
from app.utils.constants import DiagnosticStatus

# Reconnaît la dernière ligne au format "[STATUT: <MARQUEUR>]", avec ou sans
# saut de ligne/espaces finaux (le LLM ajoute parfois un espace superflu).
_STATUS_MARKER_PATTERN = re.compile(
    r"\n?\[STATUT:\s*(" + "|".join(DIAGNOSTIC_STATUS_MARKERS) + r")\]\s*$"
)

_FALLBACK_TICKET_TITLE = "Ticket créé automatiquement par le diagnostic"


@dataclass(frozen=True)
class DiagnosticResult:
    """Résultat d'un tour de diagnostic : réponse de l'agent + statut de résolution.

    `ticket` n'est renseigné que si `status is DiagnosticStatus.ESCALATE`
    (ticket réutilisé ou nouvellement créé, tâche 7) ; `None` sinon.
    """

    conversation: Conversation
    message: Message
    status: DiagnosticStatus
    ticket: Ticket | None = None


class DiagnosticService:
    """Orchestrateur du diagnostic automatique : Chat + RAG + LLM, statut de résolution en plus."""

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService | None = None,
        retriever: RetrieverService | None = None,
    ) -> None:
        self.session = session
        self._chat_service = ChatService(session, llm_service=llm_service, retriever=retriever)
        self._ticket_service = TicketService(session)

    async def diagnose(
        self,
        user: User,
        content: str,
        conversation_id: UUID | None = None,
        product_id: UUID | None = None,
    ) -> DiagnosticResult:
        """Traite un message dans le cadre d'un diagnostic et retourne le statut associé.

        Règle CDC §14 (exemple E17) : le diagnostic est conversationnel, l'IA
        vérifie avant de conclure. On n'escalade donc jamais dès le tout
        premier message d'une conversation, même si le LLM le demande : le
        statut est alors ramené à EN_COURS pour forcer au moins une relance.
        """

        is_first_exchange = await self._is_first_user_message(conversation_id, user.id)

        conversation, assistant_message = await self._chat_service.send_message(
            user,
            content,
            conversation_id=conversation_id,
            product_id=product_id,
            extra_system_instructions=DIAGNOSTIC_STATUS_INSTRUCTION,
        )

        cleaned_content, status = _extract_status(assistant_message.content)

        if is_first_exchange and status is DiagnosticStatus.ESCALATE:
            status = DiagnosticStatus.IN_PROGRESS

        if cleaned_content != assistant_message.content:
            assistant_message.content = cleaned_content
            self.session.add(assistant_message)
            await self.session.commit()
            await self.session.refresh(assistant_message)

        ticket = None
        if status is DiagnosticStatus.ESCALATE:
            ticket = await self._get_or_create_ticket(user, conversation, content, cleaned_content, product_id)

        return DiagnosticResult(conversation=conversation, message=assistant_message, status=status, ticket=ticket)

    async def _get_or_create_ticket(
        self,
        user: User,
        conversation: Conversation,
        user_content: str,
        assistant_content: str,
        product_id: UUID | None,
    ) -> Ticket:
        """Réutilise le ticket actif de la conversation s'il existe, sinon en crée un.

        Pas de nouvel appel LLM : le titre reprend celui déjà généré pour la
        conversation (ChatService), la description reprend l'échange qui a
        déclenché l'escalade.
        """

        existing = await self._ticket_service.get_active_ticket_by_conversation(conversation.id)
        if existing is not None:
            return existing

        description = f"Question du client : {user_content}\n\nRéponse du diagnostic automatique : {assistant_content}"
        data = TicketAutoCreate(
            title=conversation.title or _FALLBACK_TICKET_TITLE,
            description=description,
            product_id=product_id,
        )
        return await self._ticket_service.create_ticket(user, data, conversation_id=conversation.id)

    async def _is_first_user_message(self, conversation_id: UUID | None, user_id: UUID) -> bool:
        """Vrai si `conversation_id` est absent (nouvelle conversation) ou ne contient encore aucun message."""

        if conversation_id is None:
            return True

        history = await self._chat_service.get_history(conversation_id, user_id)
        return len(history) == 0


def _extract_status(content: str) -> tuple[str, DiagnosticStatus]:
    """Extrait le marqueur de statut de fin de réponse.

    Si le LLM a omis le marqueur ou l'a mal formé, on retombe sur EN_COURS
    plutôt que de faire échouer le diagnostic : mieux vaut continuer la
    conversation que d'escalader par erreur sur un défaut de formatage.
    """

    match = _STATUS_MARKER_PATTERN.search(content)
    if match is None:
        return content, DiagnosticStatus.IN_PROGRESS

    cleaned = content[: match.start()].rstrip()
    status = DiagnosticStatus(DIAGNOSTIC_STATUS_MARKERS[match.group(1)])
    return cleaned, status


__all__ = ["DiagnosticResult", "DiagnosticService"]
