"""Tests du timeout explicite sur les appels LLM (Semaine 7, Tâche 2, Partie 4).

Aucun de ces tests ne construit de client SDK réel ni n'ouvre de connexion
réseau : ils exercent directement `OpenAICompatibleProvider.agenerate()` avec
un client factice (comportement normal / timeout / exception fournisseur),
et vérifient par capture que chaque provider transmet bien
`settings.LLM_REQUEST_TIMEOUT_SECONDS` à son SDK. Volontairement non marqués
`external` : aucun réseau, aucune clé API réelle requise, déterministes même
en présence du bug d'environnement cacert.pem (Tâche 1).
"""
import pytest

from app.ai.exceptions import LLMRequestError
from app.ai.providers._openai_compatible import OpenAICompatibleProvider
from app.core.config import settings


class _FakeCompletions:
    def __init__(self, *, result=None, exception=None):
        self._result = result
        self._exception = exception

    async def create(self, **kwargs):
        if self._exception is not None:
            raise self._exception
        return self._result


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeOpenAIClient:
    """Double du client `AsyncOpenAI`, injecté directement (pas de réseau)."""

    def __init__(self, *, result=None, exception=None) -> None:
        self.chat = _FakeChat(_FakeCompletions(result=result, exception=exception))


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def _make_provider(*, result=None, exception=None) -> OpenAICompatibleProvider:
    """Construit un `OpenAICompatibleProvider` sans appeler `AsyncOpenAI(...)`.

    Contourne volontairement `__init__` (qui construit un vrai client SDK) :
    on ne teste ici que la logique de `agenerate()`, pas la construction du
    client (couverte séparément par `test_*_configures_timeout_from_settings`).
    """

    provider = object.__new__(OpenAICompatibleProvider)
    provider._client = _FakeOpenAIClient(result=result, exception=exception)
    provider._model = "fake-model"
    return provider


@pytest.mark.asyncio
async def test_agenerate_returns_text_on_normal_call():
    provider = _make_provider(result=_FakeResponse("Bonjour !"))

    reply = await provider.agenerate([{"role": "user", "content": "Salut"}])

    assert reply == "Bonjour !"


@pytest.mark.asyncio
async def test_agenerate_wraps_timeout_as_llm_request_error():
    """Simule le comportement du SDK quand le timeout configuré est dépassé."""

    provider = _make_provider(exception=TimeoutError("Request timed out"))

    with pytest.raises(LLMRequestError):
        await provider.agenerate([{"role": "user", "content": "Salut"}])


@pytest.mark.asyncio
async def test_agenerate_wraps_other_provider_exception_as_llm_request_error():
    provider = _make_provider(exception=ConnectionError("Provider unreachable"))

    with pytest.raises(LLMRequestError):
        await provider.agenerate([{"role": "user", "content": "Salut"}])


@pytest.mark.asyncio
async def test_agenerate_error_propagates_original_exception_message():
    provider = _make_provider(exception=TimeoutError("Request timed out after 30s"))

    with pytest.raises(LLMRequestError, match="Request timed out after 30s"):
        await provider.agenerate([{"role": "user", "content": "Salut"}])


# --- Vérification du câblage du timeout par provider (capture, sans réseau) -


def test_openai_compatible_provider_configures_timeout_from_settings(monkeypatch):
    """OpenAI / Qwen / Llama partagent `OpenAICompatibleProvider` : un seul test suffit."""

    captured = {}

    class _CapturingAsyncOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("app.ai.providers._openai_compatible.AsyncOpenAI", _CapturingAsyncOpenAI)

    OpenAICompatibleProvider(api_key="fake-key", model="fake-model")

    assert captured["timeout"] == settings.LLM_REQUEST_TIMEOUT_SECONDS


def test_gemini_provider_configures_http_options_timeout_from_settings(monkeypatch):
    from app.ai.providers import gemini_provider as gp

    captured = {}

    class _CapturingClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_genai_module = type("FakeGenaiModule", (), {"Client": _CapturingClient})
    monkeypatch.setattr(gp, "genai", fake_genai_module)
    monkeypatch.setattr(gp.settings, "GEMINI_API_KEY", "fake-key")

    gp.GeminiProvider()

    assert captured["http_options"].timeout == int(settings.LLM_REQUEST_TIMEOUT_SECONDS * 1000)


def test_mistral_provider_configures_timeout_ms_from_settings(monkeypatch):
    from app.ai.providers import mistral_provider as mp

    captured = {}

    class _CapturingMistral:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(mp, "Mistral", _CapturingMistral)
    monkeypatch.setattr(mp.settings, "MISTRAL_API_KEY", "fake-key")

    mp.MistralProvider()

    assert captured["timeout_ms"] == int(settings.LLM_REQUEST_TIMEOUT_SECONDS * 1000)


__all__: list[str] = []
