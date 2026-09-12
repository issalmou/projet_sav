"""Tests de configuration de l'application FastAPI (app.main).

Durcissement production (audit, point 3) : /docs, /redoc et le schéma
OpenAPI brut ne doivent être exposés qu'en dehors de la production.
"""
from app.core.config import settings
from app.main import app


def test_docs_endpoints_depend_on_environment():
    """Vérifie le câblage réel : actifs hors production, désactivés en production.

    Ce test s'exécute dans l'environnement courant (développement/test par
    défaut) : il vérifie la branche EFFECTIVEMENT empruntée par `app.main`,
    et documente la branche opposée sans la simuler (aucune réimportation
    de module nécessaire pour un simple test de câblage).
    """

    if settings.is_production:
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
    else:
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"


__all__: list[str] = []
