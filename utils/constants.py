"""Constantes métier partagées.

Ce module centralise les valeurs fixes issues du cahier des charges, afin
d'éviter toute divergence entre les différentes couches de l'application.
"""
from enum import Enum


class RoleName(str, Enum):
    """Rôles utilisateur authentifiables."""

    CLIENT = "client"
    TECHNICIEN = "technicien"
    RESPONSABLE_SAV = "responsable_sav"
    ADMINISTRATEUR = "administrateur"


class DocumentType(str, Enum):
    """Formats de fichier acceptés pour l'upload documentaire (CDC semaine 4, tâche 3)."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentCategory(str, Enum):
    """Catégories de la base de connaissances (CDC §13 ; cf. dossiers knowledge_base/)."""

    FAQ = "faq"
    MANUALS = "manuals"
    PROCEDURES = "procedures"
    PRODUCTS = "products"
    VIDEOS = "videos"


class DocumentStatus(str, Enum):
    """Cycle de vie d'un document de la base de connaissances."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


__all__ = ["DocumentCategory", "DocumentStatus", "DocumentType", "RoleName"]
