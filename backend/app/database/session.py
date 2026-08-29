"""
Moteur SQLAlchemy asynchrone + fabrique de sessions.

Le pool de connexions est configurable via variables d'environnement pour
répondre à l'exigence de performance et de disponibilité (99.9%) : un
pool trop petit sature sous charge, un pool trop grand épuise PostgreSQL.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,  # détecte les connexions mortes -> fiabilité / disponibilité
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI fournissant une session DB par requête, fermée automatiquement."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Utilisé au démarrage et par le health check pour vérifier la connexion PostgreSQL."""
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False