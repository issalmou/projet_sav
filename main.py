"""Point d'entrée FastAPI de l'application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.clients import router as clients_router
from app.api.documents import router as documents_router
from app.api.products import router as products_router
from app.api.roles import router as roles_router
from app.api.tickets import router as tickets_router
from app.api.users import router as users_router
from app.api.warranties import router as warranties_router
from app.core.config import settings
from app.core.logger import configure_logging, logger
from app.database.session import check_db_connection


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialise les ressources applicatives au démarrage."""

    configure_logging()
    logger.info("Starting %s in %s mode", settings.APP_NAME, settings.APP_ENV)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API backend de la plateforme IA SAV & Support Technique : authentification JWT, "
        "gestion des utilisateurs et des rôles, chat IA avec recherche documentaire (RAG) et "
        "mémoire conversationnelle, gestion des tickets de support, des produits et de leur "
        "garantie, ainsi que de la base documentaire."
    ),
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    # Durcissement production (point 3 de l'audit) : /docs, /redoc et le
    # schéma OpenAPI brut restent actifs en développement/test (défaut
    # APP_ENV=development), mais sont désactivés dès APP_ENV=production —
    # ne pas exposer la documentation interactive de l'API publiquement.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    # En dev (CORS_ALLOW_ALL), on reflète n'importe quelle origine via un regex
    # plutôt que allow_origins=["*"], afin de rester compatible avec
    # allow_credentials=True. En production, seule la liste blanche s'applique.
    allow_origins=[] if settings.cors_allow_all else settings.cors_origins,
    allow_origin_regex=".*" if settings.cors_allow_all else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(clients_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(products_router, prefix=settings.API_V1_PREFIX)
app.include_router(roles_router, prefix=settings.API_V1_PREFIX)
app.include_router(tickets_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)
app.include_router(warranties_router, prefix=settings.API_V1_PREFIX)


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict[str, str]:
    """Route racine de l'application."""

    return {"message": "AI SAV Backend is running"}


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, object]:
    """Vérifie l'état de l'application et la connexion à la base de données."""

    database_ready = await check_db_connection()
    status_value = "healthy" if database_ready else "degraded"

    return {
        "status": status_value,
        "database": "connected" if database_ready else "unavailable",
    }


__all__ = ["app"]