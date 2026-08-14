"""Routes de gestion des tickets SAV (CDC semaine 5/6).

Toutes les routes sont protégées par JWT (`get_current_user`) uniquement :
aucun rôle n'est exclu au niveau route, car chaque rôle a un accès légitime
(scope différent) aux tickets. Le filtrage par rôle/ownership est appliqué
entièrement dans `TicketService` (tâche 5) — la route ne porte que la
responsabilité HTTP (mapping des exceptions métier en codes de statut).
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketRead, TicketUpdate
from app.services.ticket_service import InvalidTechnicianRoleError, TicketPermissionError, TicketService


router = APIRouter(prefix="/tickets", tags=["Tickets"])


async def get_ticket_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> TicketService:
    """Fournit un TicketService lié à la session de la requête.

    Dépendance dédiée (comme `get_chat_service`) pour permettre aux tests
    d'injecter un TicketService via `app.dependency_overrides` si besoin.
    """

    return TicketService(db)


@router.get("/status", status_code=status.HTTP_200_OK)
async def tickets_status() -> dict[str, str]:
    """Retourne un état simple pour valider que le module est branché."""

    return {"message": "Ticket routes are ready"}


@router.post("/", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    ticket_service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    """Crée un ticket de support, toujours au nom de l'utilisateur authentifié."""

    return await ticket_service.create_ticket(current_user, payload)


@router.get("/", response_model=list[TicketRead], status_code=status.HTTP_200_OK)
async def list_tickets(
    current_user: Annotated[User, Depends(get_current_user)],
    ticket_service: Annotated[TicketService, Depends(get_ticket_service)],
) -> list[TicketRead]:
    """Liste les tickets visibles par l'utilisateur authentifié (règles d'accès : tâche 5)."""

    return await ticket_service.list_tickets(current_user)


@router.get("/{ticket_id}", response_model=TicketRead, status_code=status.HTTP_200_OK)
async def get_ticket(
    ticket_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    ticket_service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    """Retourne un ticket si l'utilisateur authentifié a le droit de le voir."""

    try:
        return await ticket_service.get_ticket(ticket_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{ticket_id}", response_model=TicketRead, status_code=status.HTTP_200_OK)
async def update_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    ticket_service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    """Met à jour un ticket si l'utilisateur authentifié a le droit de le modifier."""

    try:
        return await ticket_service.update_ticket(ticket_id, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except TicketPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except InvalidTechnicianRoleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


__all__ = ["router", "get_ticket_service"]
