"""Routes du tableau de bord.

Le module expose uniquement des endpoints préparatoires.
La logique d'agrégation des indicateurs sera ajoutée dans une phase ultérieure.
"""
from fastapi import APIRouter, status


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/status", status_code=status.HTTP_200_OK)
async def dashboard_status() -> dict[str, str]:
	"""Retourne un état simple pour valider que le module est branché."""

	return {"message": "Dashboard routes are ready"}


@router.get("/summary", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def dashboard_summary_placeholder() -> dict[str, str]:
	"""Point d'entrée préparé pour récupérer un résumé du tableau de bord."""

	return {"detail": "Dashboard summary will be implemented in a later phase"}


@router.get("/metrics", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def dashboard_metrics_placeholder() -> dict[str, str]:
	"""Point d'entrée préparé pour exposer les métriques du tableau de bord."""

	return {"detail": "Dashboard metrics will be implemented in a later phase"}


__all__ = ["router"]
