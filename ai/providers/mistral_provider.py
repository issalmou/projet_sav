"""Fournisseur LLM Mistral AI."""
import json

from mistralai.client import Mistral

from app.ai.exceptions import LLMProviderNotConfiguredError, LLMRequestError
from app.ai.providers._openai_compatible import _to_openai_messages
from app.ai.providers.base import LLMProvider, LLMResult, Message, ToolCall, ToolSpec
from app.core.config import settings


class MistralProvider(LLMProvider):
    """Fournisseur basé sur le SDK officiel `mistralai`."""

    def __init__(self) -> None:
        if not settings.MISTRAL_API_KEY:
            raise LLMProviderNotConfiguredError("MISTRAL_API_KEY is not configured")

        # `timeout_ms` est natif au SDK `mistralai` (cf. settings.LLM_REQUEST_TIMEOUT_SECONDS).
        timeout_ms = int(settings.LLM_REQUEST_TIMEOUT_SECONDS * 1000)
        self._client = Mistral(api_key=settings.MISTRAL_API_KEY, timeout_ms=timeout_ms)
        self._model = settings.MISTRAL_MODEL

    async def agenerate(self, messages: list[Message], **kwargs: object) -> str:
        try:
            response = await self._client.chat.complete_async(
                model=self._model, messages=_to_openai_messages(messages)
            )
        except Exception as exc:
            raise LLMRequestError(str(exc)) from exc

        return response.choices[0].message.content or ""

    async def agenerate_tools(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResult:
        mistral_tools = [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
            }
            for t in tools
        ]
        try:
            response = await self._client.chat.complete_async(
                model=self._model,
                messages=_to_openai_messages(messages),
                tools=mistral_tools or None,
                tool_choice="auto" if mistral_tools else None,
            )
        except Exception as exc:
            raise LLMRequestError(str(exc)) from exc

        message = response.choices[0].message
        calls: list[ToolCall] = []
        for tc in getattr(message, "tool_calls", None) or []:
            raw_args = tc.function.arguments
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args or "{}")
                except json.JSONDecodeError:
                    args = {}
            else:
                args = dict(raw_args or {})
            calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        return LLMResult(text=message.content or "", tool_calls=tuple(calls))


__all__ = ["MistralProvider"]
