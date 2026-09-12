"""Fournisseur LLM Google Gemini (fournisseur actif par défaut, cf. .env LLM_PROVIDER)."""
import uuid

from google import genai
from google.genai import types

from app.ai.exceptions import LLMProviderNotConfiguredError, LLMRequestError
from app.ai.providers.base import LLMProvider, LLMResult, Message, ToolCall, ToolSpec
from app.core.config import settings


# Gemini nomme le tour de l'assistant "model" (et non "assistant").
_ROLE_MAP = {"assistant": "model", "user": "user"}


def _to_gemini_contents(
    messages: list[Message], thought_signatures: dict[str, object] | None = None
) -> tuple[str | None, list[types.Content]]:
    """Sépare les messages système (system_instruction) des tours user/model/tool.

    `thought_signatures` (optionnel) : correspondance `tool_call.id -> thought_signature`
    capturée par `GeminiProvider` sur le PREMIER appel qui a produit ces
    `function_call`. Les modèles Gemini récents (« thinking ») exigent que ce
    jeton opaque soit ré-attaché quand on rejoue le tour dans l'historique,
    sans quoi l'API renvoie 400 INVALID_ARGUMENT (« missing a thought_signature »).
    """

    thought_signatures = thought_signatures or {}
    system_parts: list[str] = []
    contents: list[types.Content] = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "") or ""

        if role == "system":
            system_parts.append(content)
            continue

        if role == "tool":
            # L'API Gemini réelle rejette role="tool" (400 INVALID_ARGUMENT :
            # « Role 'tool' is not supported. Please use ... USER ... »).
            # Les réponses de fonction se transmettent dans un tour "user",
            # conformément aux exemples officiels google-genai.
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=message.get("name", "tool"), response={"result": content}
                        )
                    ],
                )
            )
            continue

        if role == "assistant" and message.get("tool_calls"):
            parts: list[types.Part] = []
            if content:
                parts.append(types.Part(text=content))
            for tc in message["tool_calls"]:
                part_kwargs: dict[str, object] = {
                    "function_call": types.FunctionCall(name=tc["name"], args=tc["arguments"])
                }
                signature = thought_signatures.get(tc["id"])
                if signature is not None:
                    part_kwargs["thought_signature"] = signature
                parts.append(types.Part(**part_kwargs))
            contents.append(types.Content(role="model", parts=parts))
            continue

        contents.append(types.Content(role=_ROLE_MAP.get(role, "user"), parts=[types.Part(text=content)]))

    system_instruction = "\n".join(system_parts) if system_parts else None
    return system_instruction, contents


def _to_gemini_tool(tools: list[ToolSpec]) -> types.Tool | None:
    if not tools:
        return None
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(name=t.name, description=t.description, parameters=t.parameters)
            for t in tools
        ]
    )


class GeminiProvider(LLMProvider):
    """Fournisseur basé sur le SDK officiel `google-genai`."""

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise LLMProviderNotConfiguredError("GEMINI_API_KEY is not configured")

        # `HttpOptions.timeout` est en millisecondes (SDK google-genai).
        timeout_ms = int(settings.LLM_REQUEST_TIMEOUT_SECONDS * 1000)
        http_options = types.HttpOptions(timeout=timeout_ms)
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options=http_options)
        self._model = settings.GEMINI_MODEL
        # `tool_call.id -> thought_signature` : ne survit que le temps d'un run
        # (une instance de provider par tour LangGraph, cf. SavAgent.run_turn),
        # ce qui suffit puisque les tool_calls ne sont jamais persistés en base
        # (seuls le message utilisateur et la réponse texte finale le sont).
        self._thought_signatures: dict[str, object] = {}

    async def agenerate(self, messages: list[Message], **kwargs: object) -> str:
        system_instruction, contents = _to_gemini_contents(messages, self._thought_signatures)
        config = types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model, contents=contents, config=config
            )
        except Exception as exc:  # erreurs réseau, quota, clé invalide...
            raise LLMRequestError(str(exc)) from exc

        return response.text or ""

    async def agenerate_tools(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResult:
        system_instruction, contents = _to_gemini_contents(messages, self._thought_signatures)
        tool = _to_gemini_tool(tools)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[tool] if tool else None,
            # On pilote nous-mêmes la boucle d'outils (LangGraph) : désactiver
            # l'exécution automatique du SDK.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model, contents=contents, config=config
            )
        except Exception as exc:
            raise LLMRequestError(str(exc)) from exc

        text_parts: list[str] = []
        calls: list[ToolCall] = []
        candidate = (response.candidates or [None])[0]
        parts = getattr(getattr(candidate, "content", None), "parts", None) or []
        for part in parts:
            fc = getattr(part, "function_call", None)
            if fc is not None:
                call_id = getattr(fc, "id", None) or f"call_{uuid.uuid4().hex[:12]}"
                signature = getattr(part, "thought_signature", None)
                if signature is not None:
                    # Réattaché si ce tool_call est rejoué dans l'historique
                    # (cf. `_to_gemini_contents`) — sinon 400 INVALID_ARGUMENT
                    # sur les modèles Gemini « thinking ».
                    self._thought_signatures[call_id] = signature
                calls.append(ToolCall(id=call_id, name=fc.name, arguments=dict(fc.args or {})))
            elif getattr(part, "text", None):
                text_parts.append(part.text)

        return LLMResult(text="".join(text_parts), tool_calls=tuple(calls))


__all__ = ["GeminiProvider"]
