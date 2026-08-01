"""Fournisseur LLM OpenAI (GPT)."""
from app.ai.exceptions import LLMProviderNotConfiguredError
from app.ai.providers._openai_compatible import OpenAICompatibleProvider
from app.core.config import settings


class OpenAIProvider(OpenAICompatibleProvider):
    """Fournisseur basé sur le SDK officiel `openai`."""

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise LLMProviderNotConfiguredError("OPENAI_API_KEY is not configured")

        super().__init__(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)


__all__ = ["OpenAIProvider"]
