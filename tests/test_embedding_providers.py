"""Tests de app.ai.embeddings : factory et fournisseurs (semaine 4, tâche 6).

Tous les fournisseurs sont testés au niveau sélection/instanciation, sans
appel réseau ni clé API réelle — même approche que test_llm_providers.py.
L'appel réel à Gemini (seul fournisseur configuré avec une vraie clé) est
couvert une seule fois, pour ne pas épuiser le quota gratuit à chaque
exécution des tests.
"""
import pytest

from app.ai.embeddings.e5_embedding_provider import E5EmbeddingProvider
from app.ai.embeddings.factory import EmbeddingProviderFactory
from app.ai.embeddings.gemini_embedding_provider import GeminiEmbeddingProvider
from app.ai.embeddings.llama_embedding_provider import LlamaEmbeddingProvider
from app.ai.embeddings.mistral_embedding_provider import MistralEmbeddingProvider
from app.ai.embeddings.openai_embedding_provider import OpenAIEmbeddingProvider
from app.ai.embeddings.qwen_embedding_provider import QwenEmbeddingProvider
from app.ai.exceptions import EmbeddingProviderNotConfiguredError
from app.core.config import settings


def test_factory_raises_for_unknown_provider():
    with pytest.raises(EmbeddingProviderNotConfiguredError):
        EmbeddingProviderFactory.create("does-not-exist")


def test_factory_raises_when_provider_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    with pytest.raises(EmbeddingProviderNotConfiguredError):
        EmbeddingProviderFactory.create("gemini")


def test_factory_creates_gemini_provider_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key-for-instantiation")

    provider = EmbeddingProviderFactory.create("gemini")

    assert isinstance(provider, GeminiEmbeddingProvider)


def test_factory_creates_openai_provider_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "fake-key")

    provider = EmbeddingProviderFactory.create("openai")

    assert isinstance(provider, OpenAIEmbeddingProvider)


def test_factory_creates_mistral_provider_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "MISTRAL_API_KEY", "fake-key")

    provider = EmbeddingProviderFactory.create("mistral")

    assert isinstance(provider, MistralEmbeddingProvider)


def test_factory_creates_qwen_provider_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "QWEN_API_KEY", "fake-key")

    provider = EmbeddingProviderFactory.create("qwen")

    assert isinstance(provider, QwenEmbeddingProvider)


def test_factory_creates_llama_provider_without_real_api_key():
    """Un serveur Ollama local ne requiert pas de vraie clé API."""

    provider = EmbeddingProviderFactory.create("llama")

    assert isinstance(provider, LlamaEmbeddingProvider)


def test_factory_creates_e5_provider_without_api_key():
    """E5 tourne localement (sentence-transformers) : pas de clé API requise."""

    provider = EmbeddingProviderFactory.create("e5")

    assert isinstance(provider, E5EmbeddingProvider)


def test_factory_uses_default_provider_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key")

    provider = EmbeddingProviderFactory.create()

    assert isinstance(provider, GeminiEmbeddingProvider)


def test_embedding_provider_is_independent_from_llm_provider(monkeypatch):
    """EMBEDDING_PROVIDER et LLM_PROVIDER peuvent diverger (décision validée le 2026-08-07)."""

    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key")

    provider = EmbeddingProviderFactory.create()

    assert isinstance(provider, GeminiEmbeddingProvider)


@pytest.mark.external
@pytest.mark.asyncio
async def test_gemini_embedding_real_call():
    """Seul appel réseau réel de la suite embeddings, pour valider modèle + intégration bout en bout."""

    provider = GeminiEmbeddingProvider()

    vectors = await provider.aembed(["Bonjour, ceci est un test d'embedding."])

    assert len(vectors) == 1
    assert len(vectors[0]) > 0
    assert all(isinstance(value, float) for value in vectors[0])


@pytest.mark.external
@pytest.mark.asyncio
async def test_e5_embedding_real_call():
    """E5 tourne localement : cet appel est réel mais gratuit (pas de quota à préserver)."""

    provider = E5EmbeddingProvider()

    vectors = await provider.aembed(["Bonjour, ceci est un test d'embedding."])

    assert len(vectors) == 1
    assert len(vectors[0]) > 0
    assert all(isinstance(value, float) for value in vectors[0])


__all__: list[str] = []
