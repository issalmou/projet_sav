"""Journalisation structurée de l'application.

La configuration reste autonome afin d'éviter une dépendance externe non
déclarée, tout en gardant un format JSON en production et un format texte
en développement.
"""
import json
import logging
import sys
from datetime import datetime, timezone
from logging.config import dictConfig

from app.core.config import settings


class RequestIdFilter(logging.Filter):
    """Injecte un request_id (par défaut '-') dans chaque enregistrement de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


class JsonFormatter(logging.Formatter):
    """Formate les logs en JSON sans dépendance externe.

    Le format reste volontairement simple et stable pour être consommé par
    des agrégateurs de logs en production.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Format texte lisible pour le développement local."""

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = getattr(record, "request_id", "-")
        return super().format(record)


def configure_logging() -> None:
    formatter_name = "json" if settings.LOG_JSON else "text"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": RequestIdFilter}},
            "formatters": {
                "json": {
                    "()": "app.core.logger.JsonFormatter",
                },
                "text": {
                    "()": "logging.Formatter",
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | req=%(request_id)s | %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": formatter_name,
                    "filters": ["request_id"],
                }
            },
            "root": {"handlers": ["console"], "level": settings.LOG_LEVEL},
            "loggers": {
                "uvicorn": {"handlers": ["console"], "level": settings.LOG_LEVEL, "propagate": False},
                "uvicorn.access": {"handlers": ["console"], "level": settings.LOG_LEVEL, "propagate": False},
                "sqlalchemy.engine": {
                    "handlers": ["console"],
                    "level": "WARNING",
                    "propagate": False,
                },
            },
        }
    )


logger = logging.getLogger("sav_ia")