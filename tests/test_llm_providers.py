"""Tests de app.ai.providers : factory et fournisseurs (tâche 3.3).

Tous les fournisseurs sont testés au niveau sélection/instanciation et
conversion de messages, sans appel réseau ni clé API réelle. L'appel réel à
Gemini est couvert une seule fois pour toute la suite, au niveau HTTP
(tests/test_chat_api.py), pour ne pas épuiser le quota gratuit à chaque
exécution des tests.
"""
import pytest

from app.ai.exceptions import LLMProviderNotConfiguredError
from app.ai.providers.factory import LLMProviderFactory
from app.ai.providers.gemini_provider import GeminiProvider, _to_gemini_contents
from app.ai.providers.llama_provider import LlamaProvider
from app.ai.providers.mistral_provider import MistralProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.qwen_provider import QwenProvider
from app.core.config import settings


def test_factory_raises_for_unknown_provider():
    with pytest.raises(LLMProviderNotConfiguredError):
        LLMProviderFactory.create("does-not-exist")


def test_factory_raises_when_provider_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    with pytest.raises(LLMProviderNotConfiguredError):
        LLMProviderFactory.create("gemini")


def test_factory_creates_gemini_provider_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key-for-instantiation")

    provider = LLMProviderFactory.create("gemini")

    assert isinstance(provider, GeminiProvider)


def test_factory_creates_openai_provider_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "fake-key")

    provider = LLMProviderFactory.create("openai")

    assert isinstance(provider, OpenAIProvider)


def test_factory_creates_mistral_provider_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "MISTRAL_API_KEY", "fake-key")

    provider = LLMProviderFactory.create("mistral")

    assert isinstance(provider, MistralProvider)


def test_factory_creates_qwen_provider_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "QWEN_API_KEY", "fake-key")

    provider = LLMProviderFactory.create("qwen")

    assert isinstance(provider, QwenProvider)


def test_factory_creates_llama_provider_without_real_api_key():
    """Un serveur Ollama local ne requiert pas de vraie clé API."""

    provider = LLMProviderFactory.create("llama")

    assert isinstance(provider, LlamaProvider)


def test_factory_uses_default_provider_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key")

    provider = LLMProviderFactory.create()

    assert isinstance(provider, GeminiProvider)


def test_to_gemini_contents_separates_system_instruction():
    system_instruction, contents = _to_gemini_contents(
        [
            {"role": "system", "content": "Tu es l'assistant SAV."},
            {"role": "user", "content": "Bonjour"},
        ]
    )

    assert system_instruction == "Tu es l'assistant SAV."
    assert len(contents) == 1
    assert contents[0].role == "user"


def test_to_gemini_contents_maps_assistant_role_to_model():
    _, contents = _to_gemini_contents(
        [
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Bonjour, comment puis-je vous aider ?"},
        ]
    )

    assert [content.role for content in contents] == ["user", "model"]


def test_to_gemini_contents_without_system_message_returns_none():
    system_instruction, contents = _to_gemini_contents([{"role": "user", "content": "Bonjour"}])

    assert system_instruction is None
    assert len(contents) == 1


__all__: list[str] = []
