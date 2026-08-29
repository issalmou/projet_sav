"""Ticket persistence operations."""
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ticket import Ticket

class TicketService:
    def __init__(self, session: AsyncSession): self.session = session
    async def list_tickets(self, *, user_id: UUID, staff: bool, limit=50, offset=0, status=None, priority=None):
        query = select(Ticket).order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
        if not staff: query = query.where(Ticket.created_by_id == user_id)
        if status: query = query.where(Ticket.status == status)
        if priority: query = query.where(Ticket.priority == priority)
        return list((await self.session.scalars(query)).all())
    async def get_ticket(self, ticket_id: UUID, user_id: UUID, staff: bool):
        ticket = await self.session.get(Ticket, ticket_id)
        return ticket if ticket and (staff or ticket.created_by_id == user_id) else None
    async def create_ticket(self, payload: TicketCreate, user_id: UUID):
        ticket = Ticket(**payload.model_dump(), created_by_id=user_id)
        self.session.add(ticket); await self.session.commit(); await self.session.refresh(ticket); return ticket
    async def update_ticket(self, ticket_id, payload, user_id, staff):
        ticket = await self.get_ticket(ticket_id, user_id, staff)
        if not ticket: return None
        for key, value in payload.model_dump(exclude_unset=True).items(): setattr(ticket, key, value)
        if ticket.status in {"resolved", "closed"} and ticket.resolved_at is None: ticket.resolved_at = datetime.now(timezone.utc)
        await self.session.commit(); await self.session.refresh(ticket); return ticket
    async def delete_ticket(self, ticket_id, user_id, staff):
        ticket = await self.get_ticket(ticket_id, user_id, staff)
        if not ticket: return False
        await self.session.execute(delete(Ticket).where(Ticket.id == ticket_id)); await self.session.commit(); return True
