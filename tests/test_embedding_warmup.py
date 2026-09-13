"""Tests du préchauffage best-effort du modèle d'embeddings en arrière-plan (`app.ai.embeddings.warmup`)."""
import asyncio

import pytest

from app.ai.embeddings import warmup


@pytest.fixture(autouse=True)
def _reset_warmup_state():
    """Le flag est global au processus : isole chaque test des autres."""

    warmup._warmup_started = False
    yield
    warmup._warmup_started = False


@pytest.mark.asyncio
async def test_warm_embedding_model_runs_factory_create_in_background(monkeypatch):
    calls = []
    monkeypatch.setattr(warmup.EmbeddingProviderFactory, "create", staticmethod(lambda *a, **k: calls.append(1)))

    warmup.warm_embedding_model_in_background()

    tasks = list(warmup._background_tasks)
    assert tasks, "aucune tâche de fond planifiée"
    await asyncio.gather(*tasks)

    assert calls == [1]


@pytest.mark.asyncio
async def test_warm_embedding_model_is_idempotent_per_process(monkeypatch):
    """Plusieurs conversations ouvertes coup sur coup ne doivent pas recharger le modèle en parallèle."""

    calls = []
    monkeypatch.setattr(warmup.EmbeddingProviderFactory, "create", staticmethod(lambda *a, **k: calls.append(1)))

    warmup.warm_embedding_model_in_background()
    warmup.warm_embedding_model_in_background()

    tasks = list(warmup._background_tasks)
    await asyncio.gather(*tasks)

    assert calls == [1]


@pytest.mark.asyncio
async def test_warm_embedding_model_failure_is_swallowed(monkeypatch):
    """Un échec de préchauffage (best-effort) ne doit jamais se propager à l'appelant."""

    def _boom(*args, **kwargs):
        raise RuntimeError("modèle indisponible")

    monkeypatch.setattr(warmup.EmbeddingProviderFactory, "create", staticmethod(_boom))

    warmup.warm_embedding_model_in_background()

    tasks = list(warmup._background_tasks)
    await asyncio.gather(*tasks)  # ne doit pas lever


__all__: list[str] = []
