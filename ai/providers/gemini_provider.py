"""Fournisseur LLM Google Gemini (fournisseur actif par défaut, cf. .env LLM_PROVIDER)."""
from google import genai
from google.genai import types

from app.ai.exceptions import LLMProviderNotConfiguredError, LLMRequestError
from app.ai.providers.base import LLMProvider, Message
from app.core.config import settings


# Gemini nomme le tour de l'assistant "model" (et non "assistant").
_ROLE_MAP = {"assistant": "model", "user": "user"}


def _to_gemini_contents(messages: list[Message]) -> tuple[str | None, list[types.Content]]:
    """Sépare les messages système (system_instruction) des tours user/model."""

    system_parts: list[str] = []
    contents: list[types.Content] = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")

        if role == "system":
            system_parts.append(content)
            continue

        contents.append(types.Content(role=_ROLE_MAP.get(role, "user"), parts=[types.Part(text=content)]))

    system_instruction = "\n".join(system_parts) if system_parts else None
    return system_instruction, contents


class GeminiProvider(LLMProvider):
    """Fournisseur basé sur le SDK officiel `google-genai`."""

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise LLMProviderNotConfiguredError("GEMINI_API_KEY is not configured")

        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_MODEL

    async def agenerate(self, messages: list[Message], **kwargs: object) -> str:
        system_instruction, contents = _to_gemini_contents(messages)
        config = types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model, contents=contents, config=config
            )
        except Exception as exc:  # erreurs réseau, quota, clé invalide...
            raise LLMRequestError(str(exc)) from exc

        return response.text or ""


__all__ = ["GeminiProvider"]
