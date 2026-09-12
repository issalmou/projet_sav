"""Service métier des tickets SAV.

Les règles d'accès (visibilité par rôle, ownership) sont appliquées ici,
dans le service — jamais uniquement dans la route — comme pour
`ChatService` (ownership) et `DocumentService` (ownership + rôle).
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import STAFF_ROLES, get_role_name
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketAutoCreate, TicketCreate, TicketUpdate
from app.services.ticket_assignment import pick_technician
from app.utils.constants import RoleName, TicketStatus

_TICKET_RELATIONSHIPS = (
    selectinload(Ticket.client),
    selectinload(Ticket.assigned_technician),
    selectinload(Ticket.product),
)

# Décision de conception (pas une exigence du CDC) : "closed" est le seul
# statut terminal ; "resolved" reste considéré comme actif.
_TERMINAL_TICKET_STATUSES = (TicketStatus.CLOSED.value,)


class TicketPermissionError(Exception):
    """Le ticket existe et est visible par l'utilisateur, mais il n'a pas le droit de le modifier.

    Distinct de `ValueError` (ticket introuvable, ou aucun droit de savoir
    qu'il existe) : mappé sur 403, pas 404 — même principe que
    `DocumentPermissionError` (app.services.document).
    """


class InvalidTechnicianRoleError(Exception):
    """`assigned_technician_id` référence un utilisateur existant, mais qui n'a pas le rôle technicien.

    Volontairement pas une sous-classe de `ValueError` (même raison que
    `TicketPermissionError`) : un utilisateur introuvable reste une simple
    `ValueError` (404), alors qu'un mauvais rôle est une valeur invalide
    (400) — les deux ne doivent jamais être confondus par un `except
    ValueError` générique.
    """


class InvalidClientRoleError(Exception):
    """`client_id` référence un utilisateur existant, mais qui n'a pas le rôle client.

    Même principe que `InvalidTechnicianRoleError` : pas une sous-classe de
    `ValueError` (utilisateur introuvable → 404, mauvais rôle → 400).
    """


class TicketService:
    """Orchestrateur métier pour les tickets."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_ticket(
        self, user: User, data: TicketAutoCreate, *, conversation_id: UUID | None = None
    ) -> Ticket:
        """Création automatique (self-service) : le ticket appartient toujours à `user`.

        Utilisé exclusivement par l'agent SAV (outil create_ticket) — jamais par
        la route HTTP publique, réservée au staff (voir `create_ticket_for_client`).
        `TicketAutoCreate` ne porte pas de `client_id` : le propriétaire est
        toujours l'utilisateur pour lequel le service agit.

        Le ticket est automatiquement affecté à un technicien actif choisi au
        hasard (`ticket_assignment.pick_technician`). `None` si aucun technicien
        actif n'existe.
        """

        technician_id = await pick_technician(self.session)

        return await self._persist_new_ticket(
            title=data.title,
            description=data.description,
            product_id=data.product_id,
            client_id=user.id,
            conversation_id=conversation_id,
            assigned_technician_id=technician_id,
        )

    async def create_ticket_for_client(self, staff_user: User, data: TicketCreate) -> Ticket:
        """Création manuelle par le staff, au nom du client `data.client_id`.

        Décision de conception (pas une exigence du CDC) : seul le staff peut
        créer un ticket manuellement, toujours au nom d'un client précis —
        jamais pour lui-même. Vérifié ici en plus de la route (défense en
        profondeur) : `client_id` doit avoir le rôle `client`.
        """

        if not _is_staff_or_superuser(staff_user):
            raise TicketPermissionError("Only staff can create a ticket on behalf of another client")

        await self._ensure_is_client(data.client_id)

        return await self._persist_new_ticket(
            title=data.title,
            description=data.description,
            product_id=data.product_id,
            client_id=data.client_id,
            conversation_id=None,
        )

    async def _persist_new_ticket(
        self,
        *,
        title: str,
        description: str,
        product_id: UUID | None,
        client_id: UUID,
        conversation_id: UUID | None,
        assigned_technician_id: UUID | None = None,
    ) -> Ticket:
        ticket = Ticket(
            title=title,
            description=description,
            product_id=product_id,
            client_id=client_id,
            conversation_id=conversation_id,
            assigned_technician_id=assigned_technician_id,
        )
        self.session.add(ticket)
        await self.session.commit()
        await self.session.refresh(ticket, attribute_names=["client", "assigned_technician", "product"])
        return ticket

    async def get_active_ticket_by_conversation(self, conversation_id: UUID) -> Ticket | None:
        """Retourne le ticket actif (statut non terminal) lié à `conversation_id`, s'il existe.

        Usage interne (agent SAV) pour éviter de créer
        plusieurs tickets pour une même conversation tant que le précédent
        n'est pas `closed`. Pas de vérification de permission ici : le seul
        appelant agit toujours pour le propriétaire de la conversation.
        """

        result = await self.session.execute(
            select(Ticket)
            .options(*_TICKET_RELATIONSHIPS)
            .where(
                Ticket.conversation_id == conversation_id,
                Ticket.status.not_in(_TERMINAL_TICKET_STATUSES),
            )
            .order_by(Ticket.created_at.desc())
        )
        return result.scalars().first()

    async def list_tickets(
        self,
        user: User,
        limit: int = 50,
        offset: int = 0,
        status: TicketStatus | str | None = None,
    ) -> list[Ticket]:
        """Liste les tickets visibles par `user`, selon les règles d'accès validées.

        Le périmètre de visibilité (`_scope_to_visible_tickets`) est appliqué ici,
        dans le service — jamais contournable par un paramètre de requête :
        - client     -> uniquement ses tickets (`client_id == user.id`) ;
        - technicien  -> uniquement ceux qui lui sont assignés ;
        - staff / superuser -> tous.
        Le filtre optionnel `status` se compose avec ce périmètre. Pagination
        simple (`limit`/`offset`), même pattern que `UserService.list_users`.
        """

        query = select(Ticket).options(*_TICKET_RELATIONSHIPS).order_by(Ticket.created_at.desc())
        query = _scope_to_visible_tickets(query, user)

        if status is not None:
            query = query.where(Ticket.status == (status.value if isinstance(status, TicketStatus) else status))

        result = await self.session.execute(query.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def get_ticket(self, ticket_id: UUID, user: User) -> Ticket:
        """Retourne le ticket si `user` peut le voir, sinon lève `ValueError` (404)."""

        return await self._get_visible_ticket_or_raise(ticket_id, user)

    async def update_ticket(self, ticket_id: UUID, user: User, data: TicketUpdate) -> Ticket:
        """Met à jour un ticket.

        Lève `ValueError` (404) si `user` n'a même pas le droit de voir ce
        ticket, `TicketPermissionError` (403) s'il le voit mais n'a pas le
        droit de le modifier (cas du client sur son propre ticket).
        """

        ticket = await self._get_visible_ticket_or_raise(ticket_id, user)

        if not _can_modify(ticket, user):
            raise TicketPermissionError("You are not allowed to modify this ticket")

        updates = data.model_dump(exclude_unset=True)
        if "assigned_technician_id" in updates:
            if not _can_reassign(user):
                raise TicketPermissionError("Only staff can reassign a ticket to a technician")
            if updates["assigned_technician_id"] is not None:
                await self._ensure_is_technician(updates["assigned_technician_id"])

        for field, value in updates.items():
            if isinstance(value, TicketStatus):
                value = value.value
            setattr(ticket, field, value)

        await self.session.commit()
        await self.session.refresh(ticket, attribute_names=["client", "assigned_technician", "product"])
        return ticket

    async def _ensure_is_technician(self, technician_id: UUID) -> None:
        """Vérifie que `technician_id` référence un utilisateur existant ayant le rôle technicien.

        `ValueError` (404) si l'utilisateur n'existe pas, `InvalidTechnicianRoleError`
        (400) s'il existe mais n'a pas ce rôle — même distinction que
        `DocumentService` (`ProductNotFoundError` vs `UnsupportedFileTypeError`).
        """

        candidate = await self.session.get(User, technician_id)
        if candidate is None:
            raise ValueError("Assigned technician not found")

        if get_role_name(candidate) != RoleName.TECHNICIEN.value:
            raise InvalidTechnicianRoleError("assigned_technician_id must reference a user with the technicien role")

    async def _ensure_is_client(self, client_id: UUID) -> None:
        """Vérifie que `client_id` référence un utilisateur existant ayant le rôle client.

        Même distinction que `_ensure_is_technician` : `ValueError` (404) si
        introuvable, `InvalidClientRoleError` (400) si le rôle ne convient pas.
        """

        candidate = await self.session.get(User, client_id)
        if candidate is None:
            raise ValueError("Client not found")

        if get_role_name(candidate) != RoleName.CLIENT.value:
            raise InvalidClientRoleError("client_id must reference a user with the client role")

    async def _get_visible_ticket_or_raise(self, ticket_id: UUID, user: User) -> Ticket:
        result = await self.session.execute(
            select(Ticket).options(*_TICKET_RELATIONSHIPS).where(Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()

        if ticket is None or not _can_view(ticket, user):
            raise ValueError("Ticket not found")

        return ticket


def _can_view(ticket: Ticket, user: User) -> bool:
    """Client : uniquement ses tickets. Technicien : uniquement ceux qui lui sont assignés. Staff/superuser : tous."""

    if user.is_superuser:
        return True

    role_name = get_role_name(user)
    if role_name in STAFF_ROLES:
        return True
    if role_name == RoleName.TECHNICIEN.value:
        return ticket.assigned_technician_id == user.id

    return ticket.client_id == user.id


def _can_modify(ticket: Ticket, user: User) -> bool:
    """Réservé au staff/superuser et au technicien assigné ; jamais au client, même sur son propre ticket."""

    if user.is_superuser:
        return True

    role_name = get_role_name(user)
    if role_name in STAFF_ROLES:
        return True
    if role_name == RoleName.TECHNICIEN.value:
        return ticket.assigned_technician_id == user.id

    return False


def _is_staff_or_superuser(user: User) -> bool:
    """Staff (`STAFF_ROLES`) ou superuser : condition commune à toutes les actions de gestion.

    Factorisé pour que `_can_reassign` et `create_ticket_for_client`
    partagent exactement la même règle.
    """

    if user.is_superuser:
        return True

    return get_role_name(user) in STAFF_ROLES


def _can_reassign(user: User) -> bool:
    """Seul le staff (`STAFF_ROLES`) ou un superuser peut modifier `assigned_technician_id`.

    Décision de conception (pas une exigence du CDC) : la réassignation est
    une action de gestion, jamais confiée au technicien concerné lui-même —
    même principe que `User.role_id` (`core/permissions.py`).
    """

    return _is_staff_or_superuser(user)


def _scope_to_visible_tickets(query, user: User):
    if user.is_superuser:
        return query

    role_name = get_role_name(user)
    if role_name in STAFF_ROLES:
        return query
    if role_name == RoleName.TECHNICIEN.value:
        return query.where(Ticket.assigned_technician_id == user.id)

    return query.where(Ticket.client_id == user.id)


__all__ = ["InvalidClientRoleError", "InvalidTechnicianRoleError", "TicketPermissionError", "TicketService"]
