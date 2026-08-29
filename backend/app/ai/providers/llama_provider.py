"""Fournisseur LLM Llama, servi via une API compatible OpenAI.

Par défaut pointe vers un serveur Ollama local (`LLAMA_BASE_URL`), qui
n'exige pas de clé API réelle. Le même provider fonctionne avec tout autre
service exposant Llama derrière une API compatible OpenAI (ex: Groq,
Together) en changeant `LLAMA_BASE_URL`/`LLAMA_API_KEY` dans `.env`.
"""
from app.ai.exceptions import LLMProviderNotConfiguredError
from app.ai.providers._openai_compatible import OpenAICompatibleProvider
from app.core.config import settings


class LlamaProvider(OpenAICompatibleProvider):
    """Fournisseur Llama via un endpoint compatible OpenAI (Ollama par défaut)."""

    def __init__(self) -> None:
        if not settings.LLAMA_BASE_URL:
            raise LLMProviderNotConfiguredError("LLAMA_BASE_URL is not configured")

        # Un serveur local (Ollama) n'exige pas de vraie clé, mais le SDK OpenAI
        # requiert une valeur non vide.
        api_key = settings.LLAMA_API_KEY or "not-needed"

        super().__init__(api_key=api_key, model=settings.LLAMA_MODEL, base_url=settings.LLAMA_BASE_URL)


__all__ = ["LlamaProvider"]
