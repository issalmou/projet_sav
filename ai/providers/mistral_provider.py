"""Fournisseur LLM Mistral AI."""
from mistralai.client import Mistral

from app.ai.exceptions import LLMProviderNotConfiguredError, LLMRequestError
from app.ai.providers.base import LLMProvider, Message
from app.core.config import settings


class MistralProvider(LLMProvider):
    """Fournisseur basé sur le SDK officiel `mistralai`."""

    def __init__(self) -> None:
        if not settings.MISTRAL_API_KEY:
            raise LLMProviderNotConfiguredError("MISTRAL_API_KEY is not configured")

        self._client = Mistral(api_key=settings.MISTRAL_API_KEY)
        self._model = settings.MISTRAL_MODEL

    async def agenerate(self, messages: list[Message], **kwargs: object) -> str:
        try:
            response = await self._client.chat.complete_async(model=self._model, messages=messages)
        except Exception as exc:
            raise LLMRequestError(str(exc)) from exc

        return response.choices[0].message.content or ""


__all__ = ["MistralProvider"]
