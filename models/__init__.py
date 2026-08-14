"""Registre central des modèles ORM.

Importer ce paquet (ou n'importe quel sous-module) charge tous les modèles
dans le registre SQLAlchemy. C'est nécessaire pour que les relations
déclarées par nom de classe (ex: Mapped["Role"]) puissent être résolues,
quel que soit le modèle importé en premier par le code appelant.
"""
from app.models.conversation import Conversation
from app.models.document import Document, DocumentProduct
from app.models.message import Message
from app.models.product import Product
from app.models.role import Role
from app.models.user import User

__all__ = ["Conversation", "Document", "DocumentProduct", "Message", "Product", "Role", "User"]
