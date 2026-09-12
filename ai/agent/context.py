"""Contexte d'exécution de l'agent — la « source de vérité » côté backend.

Toutes les valeurs sensibles (produit, client, conversation) proviennent de la
conversation authentifiée de l'utilisateur, JAMAIS d'un paramètre fourni par
le LLM. Les outils (`app.ai.agent.tools`) reçoivent cet objet et n'ont donc
aucun moyen de sortir du périmètre du client courant.

Les identifiants métier sont capturés (`__post_init__`) sous forme d'UUID nus
au démarrage du run : après un `rollback()` déclenché par l'échec d'un outil,
les instances ORM sont expirées mais ces UUID restent exploitables pour
recharger proprement `conversation` / `user` (cf. `tools.execute_tool`).
"""
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMService
from app.ai.rag.retriever import RetrieverService
from app.core.config import settings
from app.models.conversation import Conversation
from app.models.user import User
from app.services.ticket_service import TicketService


@dataclass
class AgentContext:
    """Contexte injecté dans chaque outil (jamais exposé au LLM)."""

    session: AsyncSession
    user: User
    conversation: Conversation
    retriever: RetrieverService
    ticket_service: TicketService
    # Utilisé par `escalate_to_technician` / `create_ticket` pour générer la
    # description du ticket (`app.ai.agent.ticket_summary`). Injectable pour les
    # tests ; `None` => `TicketSummaryService` instancie le provider par défaut.
    llm_service: LLMService | None = None

    # Sorties mutables renseignées par les outils au fil du run.
    created_ticket_id: UUID | None = None
    proposed_summary: str | None = None
    tool_trace: list[str] = field(default_factory=list)

    # Une proposition de ticket faite pendant ce run ne peut jamais être
    # confirmée dans le même run (confirmation exigée à un tour ultérieur).
    ticket_proposed_this_run: bool = False
    # Vrai si un ticket a été créé par escalade automatique pendant ce run.
    escalated_this_run: bool = False

    # Vrai si un ticket actif existe déjà depuis un tour antérieur (calculé
    # une fois par `SavAgent.run_turn`, avant tout outil) : distinct de
    # `created_ticket_id`, qui ne reflète qu'un ticket créé pendant ce run.
    # Un ticket déjà ouvert dispense le gate de relancer un diagnostic.
    has_active_ticket: bool = False

    def __post_init__(self) -> None:
        # UUID nus, insensibles à l'expiration ORM après un rollback.
        self._conversation_id: UUID = self.conversation.id
        self._user_id: UUID = self.user.id
        self._product_id: UUID = self.conversation.product_id
        # Snapshot pris à l'ouverture du tour, avant tout outil : permet au
        # gate de savoir si un diagnostic était en attente de retour client
        # AU DÉBUT du tour, indépendamment de ce qui change en cours de tour.
        self.turn_started_awaiting_feedback: bool = self.conversation.awaiting_step_feedback

    @property
    def product_id(self) -> UUID:
        return self._product_id

    @property
    def client_id(self) -> UUID:
        return self._user_id

    @property
    def conversation_id(self) -> UUID:
        return self._conversation_id

    @property
    def escalation_threshold(self) -> int:
        return settings.AGENT_ESCALATION_MAX_FAILED_ATTEMPTS

    @property
    def escalation_allowed(self) -> bool:
        """Vrai si le diagnostic a atteint le seuil autorisant un ticket automatique."""
        return self.conversation.diagnostic_attempts >= self.escalation_threshold


__all__ = ["AgentContext"]
