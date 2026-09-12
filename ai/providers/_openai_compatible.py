"""Base commune aux fournisseurs exposant une API compatible OpenAI.

OpenAI, Qwen (DashScope), Llama et Ollama partagent le même format d'appel
"chat/completions" (y compris le tool-calling) : cette classe évite de
dupliquer cette logique dans chacun des providers.

Les écarts propres à un fournisseur sont pilotés par des paramètres du
constructeur, jamais par une branche `if provider == ...` :
- `default_body` : options non standard passées dans le corps de la requête
  (ex : Ollama veut `num_ctx` pour élargir sa fenêtre de contexte) ;
- `send_tool_choice` : Ollama ne supporte pas `tool_choice` sur son endpoint
  `/v1` — il ne doit alors pas être envoyé.

La normalisation des `tool_call.id` (régénération si vide ou dupliqué) est
commune : la couche de compat OpenAI d'Ollama en renvoie parfois d'invalides,
et le graphe LangGraph s'appuie sur ces ids pour apparier les réponses d'outils.
"""
import json
import uuid

from openai import AsyncOpenAI

from app.ai.exceptions import LLMRequestError
from app.ai.providers.base import LLMProvider, LLMResult, Message, ToolCall, ToolSpec
from app.core.config import settings


def _to_openai_messages(messages: list[Message]) -> list[dict]:
    """Traduit le format interne vers les messages chat/completions d'OpenAI."""

    out: list[dict] = []
    for m in messages:
        role = m.get("role", "user")
        if role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": m["tool_call_id"],
                    "content": m.get("content", ""),
                }
            )
        elif role == "assistant" and m.get("tool_calls"):
            out.append(
                {
                    "role": "assistant",
                    "content": m.get("content") or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                        }
                        for tc in m["tool_calls"]
                    ],
                }
            )
        else:
            out.append({"role": role, "content": m.get("content", "")})
    return out


def _normalize_tool_calls(raw_tool_calls) -> list[ToolCall]:
    """Convertit les `tool_calls` du SDK en `ToolCall`, avec ids valides et uniques.

    - `arguments` non-JSON → `{}` (on ne casse jamais la boucle d'outils) ;
    - `id` vide ou déjà vu → régénéré (`call_<hex>`), comme le fait le provider
      Gemini. Le premier porteur d'un id donné le conserve.
    """

    calls: list[ToolCall] = []
    seen_ids: set[str] = set()
    for tc in raw_tool_calls or []:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except (json.JSONDecodeError, TypeError):
            args = {}
        if not isinstance(args, dict):
            args = {}

        call_id = tc.id or ""
        if not call_id or call_id in seen_ids:
            call_id = f"call_{uuid.uuid4().hex[:12]}"
        seen_ids.add(call_id)

        calls.append(ToolCall(id=call_id, name=tc.function.name, arguments=args))
    return calls


class OpenAICompatibleProvider(LLMProvider):
    """Fournisseur générique pour toute API compatible OpenAI chat/completions."""

    # Défauts de classe : les tests qui instancient via `object.__new__` (sans
    # __init__) héritent ainsi d'un comportement défini.
    _default_body: dict | None = None
    _send_tool_choice: bool = True

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        default_body: dict | None = None,
        send_tool_choice: bool = True,
    ) -> None:
        # Timeout natif du SDK `openai` (en secondes) — cf. settings.LLM_REQUEST_TIMEOUT_SECONDS.
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS)
        self._model = model
        if default_body:
            self._default_body = dict(default_body)
        self._send_tool_choice = send_tool_choice

    async def agenerate(self, messages: list[Message], **kwargs: object) -> str:
        call_kwargs: dict = dict(kwargs)
        if self._default_body:
            call_kwargs.setdefault("extra_body", self._default_body)
        try:
            response = await self._client.chat.completions.create(
                model=self._model, messages=_to_openai_messages(messages), **call_kwargs
            )
        except Exception as exc:  # erreurs réseau, quota, clé invalide, modèle absent...
            raise LLMRequestError(str(exc)) from exc

        return response.choices[0].message.content or ""

    async def agenerate_tools(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResult:
        openai_tools = [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
            }
            for t in tools
        ]

        params: dict = {
            "model": self._model,
            "messages": _to_openai_messages(messages),
            "tools": openai_tools or None,
        }
        if openai_tools and self._send_tool_choice:
            params["tool_choice"] = "auto"
        if self._default_body:
            params["extra_body"] = self._default_body

        try:
            response = await self._client.chat.completions.create(**params)
        except Exception as exc:
            raise LLMRequestError(str(exc)) from exc

        choice = response.choices[0].message
        return LLMResult(text=choice.content or "", tool_calls=tuple(_normalize_tool_calls(choice.tool_calls)))


__all__ = ["OpenAICompatibleProvider"]
