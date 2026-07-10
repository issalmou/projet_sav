"""Services liés au chat IA.

Ce module prépare la couche métier du chat sans implémenter les flux
conversationnels à ce stade de fondation.
"""
from sqlalchemy.ext.asyncio import AsyncSession


class ChatService:
	"""Orchestrateur métier pour les conversations."""

	def __init__(self, session: AsyncSession) -> None:
		self.session = session

	async def start_conversation(self) -> object:
		"""Prévu pour initialiser une conversation."""

		raise NotImplementedError("Conversation start will be implemented later")

	async def send_message(self, conversation_id: str, message: str) -> object:
		"""Prévu pour traiter un message dans une conversation."""

		raise NotImplementedError("Chat messaging will be implemented later")

	async def list_conversations(self) -> list[object]:
		"""Prévu pour lister les conversations d'un utilisateur."""

		raise NotImplementedError("Conversation listing will be implemented later")


__all__ = ["ChatService"]
