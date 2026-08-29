"""Point d'entrée FastAPI de l'application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.dashboard import router as dashboard_router
from app.api.documents import router as documents_router
from app.api.products import router as products_router
from app.api.tickets import router as tickets_router
from app.api.users import router as users_router
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
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(products_router, prefix=settings.API_V1_PREFIX)
app.include_router(tickets_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)


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