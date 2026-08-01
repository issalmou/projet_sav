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


__all__ = ["RoleName"]
