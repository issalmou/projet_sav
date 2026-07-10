"""Routes de chat IA.

Le module expose uniquement des endpoints préparatoires.
La logique conversationnelle et IA sera ajoutée dans une phase ultérieure.
"""
from fastapi import APIRouter, status


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/status", status_code=status.HTTP_200_OK)
async def chat_status() -> dict[str, str]:
	"""Retourne un état simple pour valider que le module est branché."""

	return {"message": "Chat routes are ready"}


@router.post("/sessions", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_chat_session_placeholder() -> dict[str, str]:
	"""Point d'entrée préparé pour créer une session de conversation."""

	return {"detail": "Chat session creation will be implemented in a later phase"}


@router.post("/messages", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def send_message_placeholder() -> dict[str, str]:
	"""Point d'entrée préparé pour envoyer un message."""

	return {"detail": "Chat messaging will be implemented in a later phase"}


__all__ = ["router"]
