"""Authenticated ticket endpoints."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user, get_db_session
from app.core.permissions import STAFF_ROLES, get_role_name
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketRead, TicketUpdate
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])
def is_staff(user): return user.is_superuser or get_role_name(user) in STAFF_ROLES

@router.get("/", response_model=list[TicketRead])
async def list_tickets(current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db_session)], limit=50, offset=0, status=None, priority=None):
    return await TicketService(db).list_tickets(user_id=current_user.id, staff=is_staff(current_user), limit=min(limit, 100), offset=offset, status=status, priority=priority)

@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket_id: UUID, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db_session)]):
    ticket = await TicketService(db).get_ticket(ticket_id, current_user.id, is_staff(current_user))
    if not ticket: raise HTTPException(404, "Ticket not found")
    return ticket

@router.post("/", response_model=TicketRead, status_code=201)
async def create_ticket(payload: TicketCreate, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db_session)]):
    return await TicketService(db).create_ticket(payload, current_user.id)

@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(ticket_id: UUID, payload: TicketUpdate, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db_session)]):
    ticket = await TicketService(db).update_ticket(ticket_id, payload, current_user.id, is_staff(current_user))
    if not ticket: raise HTTPException(404, "Ticket not found")
    return ticket

@router.delete("/{ticket_id}", status_code=204)
async def delete_ticket(ticket_id: UUID, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db_session)]):
    if not await TicketService(db).delete_ticket(ticket_id, current_user.id, is_staff(current_user)): raise HTTPException(404, "Ticket not found")
