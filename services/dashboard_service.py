"""Services liés au tableau de bord.

Ce module prépare la couche métier du dashboard sans implémenter les
agrégations de métriques à ce stade de fondation.
"""
from sqlalchemy.ext.asyncio import AsyncSession


class DashboardService:
	"""Orchestrateur métier pour les indicateurs du tableau de bord."""

	def __init__(self, session: AsyncSession) -> None:
		self.session = session

	async def get_summary(self) -> dict[str, object]:
		"""Prévu pour retourner un résumé global des indicateurs."""

		raise NotImplementedError("Dashboard summary will be implemented later")

	async def get_metrics(self) -> dict[str, object]:
		"""Prévu pour retourner les métriques détaillées du tableau de bord."""

		raise NotImplementedError("Dashboard metrics will be implemented later")


__all__ = ["DashboardService"]
