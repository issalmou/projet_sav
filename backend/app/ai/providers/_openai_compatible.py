"""Base commune aux fournisseurs exposant une API compatible OpenAI.

OpenAI, Qwen (DashScope) et Llama (Ollama ou tout endpoint compatible)
partagent le même format d'appel "chat/completions" : cette classe évite de
dupliquer cette logique dans chacun des trois providers.
"""
from openai import AsyncOpenAI

from app.ai.exceptions import LLMRequestError
from app.ai.providers.base import LLMProvider, Message


class OpenAICompatibleProvider(LLMProvider):
    """Fournisseur générique pour toute API compatible OpenAI chat/completions."""

    def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def agenerate(self, messages: list[Message], **kwargs: object) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model, messages=messages, **kwargs
            )
        except Exception as exc:  # erreurs réseau, quota, clé invalide...
            raise LLMRequestError(str(exc)) from exc

        return response.choices[0].message.content or ""


__all__ = ["OpenAICompatibleProvider"]
