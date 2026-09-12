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
from app.ai.providers.ollama_provider import OllamaProvider
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


def test_factory_creates_ollama_provider_without_real_api_key():
    """Le fournisseur Ollama dédié s'instancie sans clé API (serveur local).

    Comportement détaillé couvert dans `tests/test_ollama_provider.py`.
    """

    provider = LLMProviderFactory.create("ollama")

    assert isinstance(provider, OllamaProvider)


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


# --- Traduction des messages avec outils (tool-calling multi-fournisseur) ----


def test_openai_message_translation_handles_tool_calls_and_results():
    from app.ai.providers._openai_compatible import _to_openai_messages

    internal = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "name": "search_docs", "arguments": {"query": "x"}}]},
        {"role": "tool", "tool_call_id": "c1", "name": "search_docs", "content": "résultat"},
    ]
    out = _to_openai_messages(internal)

    assert out[2]["tool_calls"][0]["id"] == "c1"
    assert out[2]["tool_calls"][0]["function"]["name"] == "search_docs"
    assert '"query": "x"' in out[2]["tool_calls"][0]["function"]["arguments"]
    assert out[3] == {"role": "tool", "tool_call_id": "c1", "content": "résultat"}


def test_gemini_contents_translate_tool_calls_and_function_responses():
    """La réponse d'outil est un tour "user" — l'API Gemini réelle rejette
    role="tool" (400 INVALID_ARGUMENT), vérifié par le test `external`
    `test_real_gemini_tool_calling_round_trip`."""

    _, contents = _to_gemini_contents(
        [
            {"role": "user", "content": "q"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "name": "get_warranty", "arguments": {}}]},
            {"role": "tool", "tool_call_id": "c1", "name": "get_warranty", "content": "24 mois"},
        ]
    )

    assert [c.role for c in contents] == ["user", "model", "user"]
    assert contents[1].parts[0].function_call.name == "get_warranty"
    assert contents[2].parts[0].function_response.name == "get_warranty"


# --- Round-trip tool-calling RÉEL (exclu de la suite par défaut) ------------


@pytest.mark.external
@pytest.mark.asyncio
async def test_real_gemini_tool_calling_round_trip():
    """RÉEL — nécessite GEMINI_API_KEY (quota gratuit). Exclu par défaut
    (`addopts = -m "not external"`).

    Vérifie la boucle complète : LLM demande un outil → on ré-injecte le
    résultat de l'outil → le LLM produit une réponse finale texte.
    """

    from app.ai.providers.base import ToolSpec

    provider = LLMProviderFactory.create("gemini")
    spec = ToolSpec(
        name="get_warranty",
        description="Retourne la durée de garantie du produit.",
        parameters={"type": "object", "properties": {}},
    )
    messages = [
        {"role": "system", "content": "Tu es un agent SAV. Utilise get_warranty pour répondre à toute question de garantie."},
        {"role": "user", "content": "Quelle est la durée de garantie de mon produit ?"},
    ]

    first = await provider.agenerate_tools(messages, [spec])
    assert first.tool_calls, "Gemini n'a demandé aucun outil"
    call = first.tool_calls[0]
    assert call.name == "get_warranty"

    messages.append({"role": "assistant", "content": first.text, "tool_calls": [call.as_message()]})
    messages.append({"role": "tool", "tool_call_id": call.id, "name": call.name, "content": "Garantie : 24 mois."})

    second = await provider.agenerate_tools(messages, [spec])
    assert second.text and "24" in second.text


__all__: list[str] = []
