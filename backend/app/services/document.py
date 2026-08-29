"""Services liés aux documents.

Ce module prépare la couche métier documentaire sans implémenter les
opérations de stockage à ce stade de fondation.
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class DocumentService:
	"""Orchestrateur métier pour les documents."""

	def __init__(self, session: AsyncSession) -> None:
		self.session = session

	async def list_documents(self) -> list[object]:
		"""Prévu pour retourner la liste des documents."""

		raise NotImplementedError("Document listing will be implemented later")

	async def get_document(self, document_id: UUID) -> object:
		"""Prévu pour retourner un document par identifiant."""

		raise NotImplementedError("Document retrieval will be implemented later")

	async def upload_document(self, payload: object) -> object:
		"""Prévu pour déposer un document."""

		raise NotImplementedError("Document upload will be implemented later")

	async def delete_document(self, document_id: UUID) -> object:
		"""Prévu pour supprimer un document."""

		raise NotImplementedError("Document deletion will be implemented later")


__all__ = ["DocumentService"]
