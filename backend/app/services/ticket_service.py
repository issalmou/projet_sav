"""Services liés aux tickets SAV.

Ce module prépare la couche métier des tickets sans implémenter les flux
de traitement à ce stade de fondation.
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class TicketService:
	"""Orchestrateur métier pour les tickets."""

	def __init__(self, session: AsyncSession) -> None:
		self.session = session

	async def list_tickets(self) -> list[object]:
		"""Prévu pour retourner la liste des tickets."""

		raise NotImplementedError("Ticket listing will be implemented later")

	async def get_ticket(self, ticket_id: UUID) -> object:
		"""Prévu pour retourner un ticket par identifiant."""

		raise NotImplementedError("Ticket retrieval will be implemented later")

	async def create_ticket(self, payload: object) -> object:
		"""Prévu pour créer un ticket."""

		raise NotImplementedError("Ticket creation will be implemented later")

	async def update_ticket(self, ticket_id: UUID, payload: object) -> object:
		"""Prévu pour mettre à jour un ticket."""

		raise NotImplementedError("Ticket update will be implemented later")

	async def close_ticket(self, ticket_id: UUID) -> object:
		"""Prévu pour clôturer un ticket."""

		raise NotImplementedError("Ticket closing will be implemented later")


__all__ = ["TicketService"]
