"""Routes de gestion des tickets SAV.

Le module expose uniquement des endpoints préparatoires.
La logique métier tickets sera ajoutée dans une phase ultérieure.
"""
from fastapi import APIRouter, status


router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("/status", status_code=status.HTTP_200_OK)
async def tickets_status() -> dict[str, str]:
	"""Retourne un état simple pour valider que le module est branché."""

	return {"message": "Ticket routes are ready"}


@router.get("/", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def list_tickets_placeholder() -> dict[str, str]:
	"""Point d'entrée préparé pour lister les tickets."""

	return {"detail": "Ticket listing will be implemented in a later phase"}


@router.post("/", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_ticket_placeholder() -> dict[str, str]:
	"""Point d'entrée préparé pour créer un ticket SAV."""

	return {"detail": "Ticket creation will be implemented in a later phase"}


@router.patch("/{ticket_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def update_ticket_placeholder(ticket_id: str) -> dict[str, str]:
	"""Point d'entrée préparé pour mettre à jour un ticket."""

	return {"detail": f"Ticket {ticket_id} update will be implemented in a later phase"}


__all__ = ["router"]
