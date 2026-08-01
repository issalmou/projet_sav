"""Fournisseur LLM Qwen (Alibaba Cloud DashScope, API compatible OpenAI)."""
from app.ai.exceptions import LLMProviderNotConfiguredError
from app.ai.providers._openai_compatible import OpenAICompatibleProvider
from app.core.config import settings


class QwenProvider(OpenAICompatibleProvider):
    """Fournisseur Qwen via l'endpoint "compatible-mode" de DashScope."""

    def __init__(self) -> None:
        if not settings.QWEN_API_KEY:
            raise LLMProviderNotConfiguredError("QWEN_API_KEY is not configured")

        super().__init__(
            api_key=settings.QWEN_API_KEY, model=settings.QWEN_MODEL, base_url=settings.QWEN_BASE_URL
        )


__all__ = ["QwenProvider"]
