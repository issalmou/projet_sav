"""Tests du fournisseur LLM Ollama (`app.ai.providers.ollama_provider`).

La suite par défaut n'exige NI serveur Ollama NI réseau : le client
`AsyncOpenAI` est remplacé par un double (`_FakeAsyncOpenAI`). Un unique test
marqué `external` exerce un vrai serveur Ollama local (exclu par défaut via
`addopts = -m "not external"`).

Couverture : factory, configuration, normalisation d'URL, `agenerate`,
`agenerate_tools` (plusieurs appels, JSON valide/invalide, ids vides/dupliqués),
absence de `tool_choice`, `num_ctx` transmis, erreurs (réseau, modèle absent,
timeout, réponse vide), et non-régression des autres fournisseurs.
"""
import pytest

from app.ai.exceptions import LLMProviderNotConfiguredError, LLMRequestError
from app.ai.providers.base import ToolSpec
from app.ai.providers.factory import LLMProviderFactory
from app.ai.providers.ollama_provider import OllamaProvider, _normalize_base_url
from app.core.config import settings

_SPEC = ToolSpec(
    name="search_docs",
    description="Recherche dans la base documentaire du produit.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
)


# --- Doubles du SDK openai ------------------------------------------------


class _FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.function = _FakeFunction(name, arguments)


class _FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _FakeResponse:
    def __init__(self, content=None, tool_calls=None):
        self.choices = [type("_Choice", (), {"message": _FakeMessage(content, tool_calls)})()]


class _FakeCompletions:
    def __init__(self):
        self.calls: list[dict] = []
        self.response = _FakeResponse(content="Réponse du modèle local.")
        self.exception: Exception | None = None

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exception is not None:
            raise self.exception
        return self.response


class _FakeAsyncOpenAI:
    last_instance = None

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.chat = type("_Chat", (), {})()
        self.chat.completions = _FakeCompletions()
        _FakeAsyncOpenAI.last_instance = self


@pytest.fixture
def fake_openai(monkeypatch):
    """Remplace `AsyncOpenAI` et fixe des réglages Ollama déterministes."""

    monkeypatch.setattr("app.ai.providers._openai_compatible.AsyncOpenAI", _FakeAsyncOpenAI)
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "qwen2.5:7b")
    monkeypatch.setattr(settings, "OLLAMA_API_KEY", None)
    monkeypatch.setattr(settings, "OLLAMA_NUM_CTX", 8192)
    _FakeAsyncOpenAI.last_instance = None
    return _FakeAsyncOpenAI


def _completions(fake_openai) -> _FakeCompletions:
    return fake_openai.last_instance.chat.completions


# --- Normalisation d'URL -------------------------------------------------


def test_normalize_base_url_appends_v1_when_missing():
    assert _normalize_base_url("http://localhost:11434") == "http://localhost:11434/v1"
    assert _normalize_base_url("http://localhost:11434/") == "http://localhost:11434/v1"
    assert _normalize_base_url("http://ollama.internal:11434  ") == "http://ollama.internal:11434/v1"


def test_normalize_base_url_keeps_existing_v1():
    assert _normalize_base_url("http://localhost:11434/v1") == "http://localhost:11434/v1"
    assert _normalize_base_url("http://localhost:11434/v1/") == "http://localhost:11434/v1"


# --- Factory / configuration ------------------------------------------


def test_factory_creates_ollama_provider(fake_openai):
    assert isinstance(LLMProviderFactory.create("ollama"), OllamaProvider)


def test_factory_uses_ollama_when_configured_as_default(fake_openai, monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")
    assert isinstance(LLMProviderFactory.create(), OllamaProvider)


def test_ollama_raises_when_base_url_missing(fake_openai, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "")
    with pytest.raises(LLMProviderNotConfiguredError):
        OllamaProvider()


def test_ollama_configures_client_from_settings(fake_openai, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama-host:11434")  # sans /v1
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3.1:8b")

    provider = OllamaProvider()

    init = fake_openai.last_instance.init_kwargs
    assert init["base_url"] == "http://ollama-host:11434/v1"
    assert init["api_key"] == "ollama"  # placeholder non vide exigé par le SDK
    assert init["timeout"] == settings.LLM_REQUEST_TIMEOUT_SECONDS
    assert provider._model == "llama3.1:8b"


def test_ollama_uses_explicit_api_key_when_set(fake_openai, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_API_KEY", "proxy-token")
    OllamaProvider()
    assert fake_openai.last_instance.init_kwargs["api_key"] == "proxy-token"


# --- agenerate --------------------------------------------------------


@pytest.mark.asyncio
async def test_agenerate_returns_model_text(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(content="Bonjour du modèle local.")

    assert await provider.agenerate([{"role": "user", "content": "Salut"}]) == "Bonjour du modèle local."


@pytest.mark.asyncio
async def test_configured_model_is_sent_in_every_request(fake_openai, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "mistral-nemo")
    provider = OllamaProvider()

    await provider.agenerate([{"role": "user", "content": "x"}])
    await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    assert [c["model"] for c in _completions(fake_openai).calls] == ["mistral-nemo", "mistral-nemo"]


@pytest.mark.asyncio
async def test_agenerate_empty_content_returns_empty_string(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(content=None)

    assert await provider.agenerate([{"role": "user", "content": "x"}]) == ""


@pytest.mark.asyncio
async def test_agenerate_sends_num_ctx_in_request_body(fake_openai, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_NUM_CTX", 16384)
    provider = OllamaProvider()

    await provider.agenerate([{"role": "user", "content": "x"}])

    assert _completions(fake_openai).calls[0]["extra_body"] == {"num_ctx": 16384}


@pytest.mark.asyncio
async def test_agenerate_omits_num_ctx_when_zero(fake_openai, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_NUM_CTX", 0)
    provider = OllamaProvider()

    await provider.agenerate([{"role": "user", "content": "x"}])

    assert "extra_body" not in _completions(fake_openai).calls[0]


# --- agenerate_tools -------------------------------------------------


@pytest.mark.asyncio
async def test_agenerate_tools_never_sends_tool_choice(fake_openai):
    """L'endpoint /v1 d'Ollama ne supporte pas `tool_choice`."""

    provider = OllamaProvider()
    await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    call = _completions(fake_openai).calls[0]
    assert "tool_choice" not in call
    assert call["tools"][0]["function"]["name"] == "search_docs"


@pytest.mark.asyncio
async def test_agenerate_tools_parses_multiple_calls_and_json_args(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(
        tool_calls=[
            _FakeToolCall("call_1", "search_docs", '{"query": "erreur E17"}'),
            _FakeToolCall("call_2", "get_warranty", "{}"),
        ]
    )

    result = await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    assert [c.name for c in result.tool_calls] == ["search_docs", "get_warranty"]
    assert result.tool_calls[0].arguments == {"query": "erreur E17"}
    assert result.tool_calls[1].arguments == {}


@pytest.mark.asyncio
async def test_agenerate_tools_invalid_json_arguments_become_empty_dict(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(
        tool_calls=[_FakeToolCall("c1", "search_docs", "{query: pas du json")]
    )

    result = await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    assert result.tool_calls[0].arguments == {}


@pytest.mark.asyncio
async def test_agenerate_tools_non_dict_json_arguments_become_empty_dict(fake_openai):
    """Un modèle local peut renvoyer une liste/chaîne JSON au lieu d'un objet."""

    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(
        tool_calls=[_FakeToolCall("c1", "search_docs", "[1, 2, 3]")]
    )

    result = await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    assert result.tool_calls[0].arguments == {}


@pytest.mark.asyncio
async def test_agenerate_tools_none_arguments_become_empty_dict(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(
        tool_calls=[_FakeToolCall("c1", "get_warranty", None)]
    )

    result = await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    assert result.tool_calls[0].arguments == {}


@pytest.mark.asyncio
async def test_agenerate_tools_malformed_response_without_tool_calls_attr(fake_openai):
    """Réponse « texte seul » : ni exception, ni tool_calls fantômes."""

    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(content="Réponse directe.", tool_calls=None)

    result = await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    assert result.text == "Réponse directe."
    assert result.tool_calls == ()


@pytest.mark.asyncio
async def test_agenerate_tools_regenerates_empty_ids_uniquely(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(
        tool_calls=[
            _FakeToolCall("", "search_docs", "{}"),
            _FakeToolCall("", "get_warranty", "{}"),
        ]
    )

    result = await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    ids = [c.id for c in result.tool_calls]
    assert all(ids), "un id vide n'a pas été régénéré"
    assert len(set(ids)) == 2, "les ids régénérés ne sont pas uniques"


@pytest.mark.asyncio
async def test_agenerate_tools_regenerates_duplicate_ids(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(
        tool_calls=[
            _FakeToolCall("dup", "search_docs", "{}"),
            _FakeToolCall("dup", "get_warranty", "{}"),
        ]
    )

    result = await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    ids = [c.id for c in result.tool_calls]
    assert ids[0] == "dup"  # le premier porteur conserve l'id
    assert len(set(ids)) == 2


@pytest.mark.asyncio
async def test_agenerate_tools_keeps_valid_ids(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(
        tool_calls=[_FakeToolCall("call_abc123", "search_docs", "{}")]
    )

    result = await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    assert result.tool_calls[0].id == "call_abc123"


@pytest.mark.asyncio
async def test_agenerate_tools_text_only_response_has_no_tool_calls(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(content="Voici la réponse directe.")

    result = await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    assert result.text == "Voici la réponse directe."
    assert result.tool_calls == ()


@pytest.mark.asyncio
async def test_tool_calls_output_matches_graph_contract(fake_openai):
    """Le `LLMResult` d'Ollama doit être consommable par `app.ai.agent.graph`
    sans adaptation : `agent_node` fait `tc.as_message()`, `tools_node` lit
    `tc["name"]`, `tc["id"]`, `tc.get("arguments", {})`."""

    provider = OllamaProvider()
    _completions(fake_openai).response = _FakeResponse(
        tool_calls=[
            _FakeToolCall("", "search_docs", '{"query": "erreur E17"}'),
            _FakeToolCall("call_2", "get_warranty", "{}"),
        ]
    )

    result = await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])

    as_messages = [tc.as_message() for tc in result.tool_calls]  # ce que fait agent_node
    assert all(set(m) == {"id", "name", "arguments"} for m in as_messages)
    assert [m["name"] for m in as_messages] == ["search_docs", "get_warranty"]
    assert as_messages[0]["arguments"] == {"query": "erreur E17"}
    assert all(m["id"] for m in as_messages) and len({m["id"] for m in as_messages}) == 2
    # tools_node ré-émet des messages `tool` appariables
    tool_msgs = [
        {"role": "tool", "tool_call_id": m["id"], "name": m["name"], "content": "…"}
        for m in as_messages
    ]
    assert {t["tool_call_id"] for t in tool_msgs} == {m["id"] for m in as_messages}


# --- Erreurs -------------------------------------------------------


@pytest.mark.asyncio
async def test_agenerate_wraps_network_error(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).exception = ConnectionError("Connection refused")

    with pytest.raises(LLMRequestError, match="Connection refused"):
        await provider.agenerate([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_agenerate_tools_wraps_model_not_found(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).exception = Exception('model "qwen2.5:7b" not found, try pulling it first')

    with pytest.raises(LLMRequestError, match="not found"):
        await provider.agenerate_tools([{"role": "user", "content": "x"}], [_SPEC])


@pytest.mark.asyncio
async def test_agenerate_wraps_timeout(fake_openai):
    provider = OllamaProvider()
    _completions(fake_openai).exception = TimeoutError("Request timed out")

    with pytest.raises(LLMRequestError):
        await provider.agenerate([{"role": "user", "content": "x"}])


# --- Non-régression des autres fournisseurs ------------------------


def test_adding_ollama_does_not_break_other_providers(fake_openai, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "fake")
    monkeypatch.setattr(settings, "MISTRAL_API_KEY", "fake")
    monkeypatch.setattr(settings, "QWEN_API_KEY", "fake")

    for name in ("gemini", "openai", "mistral", "qwen", "llama", "ollama"):
        assert LLMProviderFactory.create(name) is not None


def test_llama_provider_still_sends_tool_choice(fake_openai):
    """Le fournisseur générique `llama` n'est PAS affecté par la spécificité Ollama."""

    from app.ai.providers.llama_provider import LlamaProvider

    provider = LlamaProvider()
    assert provider._send_tool_choice is True


# --- Test réel (exclu par défaut) --------------------------------


@pytest.mark.external
@pytest.mark.asyncio
async def test_real_local_ollama_supports_tool_calling():
    """RÉEL — exige `ollama serve` + `ollama pull <OLLAMA_MODEL>`.

    Exclu de la suite par défaut (`addopts = -m "not external"`). Vérifie le
    critère bloquant du modèle cible : sur une question technique, il DÉCIDE
    d'appeler `search_docs` et renvoie des arguments JSON exploitables, avec
    un id de tool call non vide.

    Appelle directement `OllamaProvider.agenerate_tools` avec un prompt
    système MINIMAL (une seule ligne), volontairement plus faible que le
    prompt de production (`app/ai/agent/prompts.py`) : l'objectif est de
    mesurer la capacité BRUTE du modèle à choisir un tool call, sans le filet
    de sécurité du graphe (garde-fou B6, relance A1). Ce test ne couvre donc
    QUE le fournisseur — la fiabilité du backend en production face à un
    modèle qui n'appelle pas l'outil est couverte indépendamment, sans
    Ollama, par `test_gate_does_not_loop_forever_when_llm_never_complies` et
    `test_force_invariant_escalates_when_llm_ignores_escalation_nudge`
    (app/tests/test_agent.py), qui prouvent que le backend force lui-même
    l'invariant quand le modèle n'obéit jamais.

    Audit de stabilisation (2026-09) : qwen2.5:3b est confirmé NON
    déterministe sur ce prompt minimal — 5 succès sur 6 exécutions isolées
    consécutives (même serveur, même modèle), l'unique échec observé étant
    une réponse texte cohérente et pertinente qui ÉVOQUE la documentation
    sans jamais appeler l'outil (jamais un timeout, jamais une réponse
    malformée). Un échec ponctuel de ce test reflète donc une variance
    d'échantillonnage du modèle, pas une régression du code ni un problème
    d'environnement — voir le rapport d'audit pour la classification
    complète. Ne PAS transformer cet échec en vert par retry, timeout
    agrandi, suppression du test ou assertion affaiblie : la variance
    observée est elle-même l'information utile."""

    provider = OllamaProvider()

    result = await provider.agenerate_tools(
        [
            {
                "role": "system",
                "content": "Tu es un agent SAV. Utilise l'outil search_docs pour toute question technique.",
            },
            {"role": "user", "content": "Mon imprimante affiche l'erreur E17, que faire ?"},
        ],
        [_SPEC],
    )

    assert result.tool_calls, "le modèle Ollama n'a demandé aucun outil"
    assert result.tool_calls[0].name == "search_docs"
    assert isinstance(result.tool_calls[0].arguments, dict)
    assert result.tool_calls[0].id


@pytest.mark.external
@pytest.mark.asyncio
async def test_real_local_ollama_tool_calling_round_trip():
    """RÉEL — boucle complète Ollama : question FR → tool_call search_docs →
    résultat de l'outil ré-injecté → réponse finale texte du modèle.

    Échoue clairement si : Ollama n'est pas démarré / le modèle n'est pas
    téléchargé / le modèle ne gère pas correctement le tool-calling.

    Même nature que `test_real_local_ollama_supports_tool_calling` (voir sa
    docstring pour l'analyse complète du non-déterminisme observé) : prompt
    système minimal, fournisseur brut sans le filet de sécurité du graphe.
    Un échec isolé et non reproductible n'indique pas une régression."""

    provider = OllamaProvider()
    messages = [
        {"role": "system", "content": "Tu es un agent SAV francophone. Utilise search_docs pour toute question technique, puis réponds en français."},
        {"role": "user", "content": "Mon imprimante affiche l'erreur E17. Que dois-je faire ?"},
    ]

    first = await provider.agenerate_tools(messages, [_SPEC])
    assert first.tool_calls and first.tool_calls[0].name == "search_docs", (
        "le modèle Ollama configuré ne déclenche pas le tool-calling attendu"
    )
    call = first.tool_calls[0]

    messages.append({"role": "assistant", "content": first.text, "tool_calls": [call.as_message()]})
    messages.append(
        {
            "role": "tool",
            "tool_call_id": call.id,
            "name": call.name,
            "content": "Procédure E17 : vérifier le bac papier, retirer tout bourrage, puis redémarrer l'imprimante.",
        }
    )

    second = await provider.agenerate_tools(messages, [_SPEC])
    assert second.text.strip(), "le modèle n'a pas produit de réponse finale après le résultat de l'outil"


__all__: list[str] = []
