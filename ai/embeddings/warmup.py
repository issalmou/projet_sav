"""Préchauffage best-effort du modèle d'embeddings, en arrière-plan.

Déclenché à l'ouverture d'une conversation (`ChatService.open_conversation`) :
le modèle est ainsi déjà chargé quand le premier message arrive, sans faire
porter ce coût (plusieurs secondes, chargement depuis le disque) sur la
réponse HTTP de création de conversation elle-même, ni bloquer la boucle
d'événements (le chargement, synchrone, tourne dans un thread).
"""
import asyncio

from app.ai.embeddings.factory import EmbeddingProviderFactory
from app.core.logger import logger

_warmup_started = False
# Référence forte obligatoire : sans elle, une tâche asyncio non référencée
# peut être détruite par le garbage collector avant sa fin.
_background_tasks: set[asyncio.Task] = set()


def warm_embedding_model_in_background() -> None:
    """Démarre le chargement du modèle d'embeddings en tâche de fond (une seule
    fois par processus). Ne bloque jamais l'appelant et n'échoue jamais :
    en cas de problème, le premier message réel rechargera le modèle normalement
    (comportement déjà correct sans ce préchauffage, juste plus lent une fois).
    """

    global _warmup_started
    if _warmup_started:
        return
    _warmup_started = True

    task = asyncio.create_task(_do_warmup())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _do_warmup() -> None:
    try:
        await asyncio.to_thread(EmbeddingProviderFactory.create)
    except Exception:
        logger.warning("Préchauffage du modèle d'embeddings échoué (sans impact : rechargé au 1er message)", exc_info=True)


__all__ = ["warm_embedding_model_in_background"]
