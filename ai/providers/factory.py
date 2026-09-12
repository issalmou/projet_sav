"""Sélection du fournisseur LLM actif.

Seule cette classe connaît la correspondance entre `LLM_PROVIDER` (.env) et
les classes concrètes de `ai/providers/`. Le reste de l'application
(ai/llm.py, services/chat_service.py) ne manipule que l'interface
`LLMProvider` : ajouter un nouveau fournisseur se limite à créer son module
et l'enregistrer ici.
"""
from app.ai.exceptions import LLMProviderNotConfiguredError
from app.ai.providers.base import LLMProvider
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.llama_provider import LlamaProvider
from app.ai.providers.mistral_provider import MistralProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.qwen_provider import QwenProvider
from app.core.config import settings


class LLMProviderFactory:
    """Instancie le fournisseur LLM configuré via `settings.LLM_PROVIDER`."""

    _REGISTRY: dict[str, type[LLMProvider]] = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "mistral": MistralProvider,
        "qwen": QwenProvider,
        "llama": LlamaProvider,
        "ollama": OllamaProvider,
    }

    @classmethod
    def create(cls, provider_name: str | None = None) -> LLMProvider:
        """Retourne une instance du fournisseur demandé (ou celui configuré par défaut)."""

        name = (provider_name or settings.LLM_PROVIDER).strip().lower()
        provider_cls = cls._REGISTRY.get(name)

        if provider_cls is None:
            raise LLMProviderNotConfiguredError(
                f"Unknown LLM provider '{name}'. Available: {', '.join(cls._REGISTRY)}"
            )

        return provider_cls()


__all__ = ["LLMProviderFactory"]
