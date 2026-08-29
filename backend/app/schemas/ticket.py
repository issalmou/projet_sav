"""Pydantic contracts for tickets."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    category: str | None = None
    priority: str = "medium"
    product_id: UUID | None = None
    assignee_id: UUID | None = None

class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    priority: str | None = None
    status: str | None = None
    product_id: UUID | None = None
    assignee_id: UUID | None = None

class TicketMessageCreate(BaseModel):
    content: str = Field(min_length=1)

class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str
    status: str
    priority: str
    category: str | None
    created_by_id: UUID
    assignee_id: UUID | None
    product_id: UUID | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

__all__ = ["TicketCreate", "TicketUpdate", "TicketMessageCreate", "TicketRead"]
