"""Fournisseur LLM Ollama — serveur de modèles local exposant une API compatible OpenAI.

Distinct du fournisseur générique `llama` : celui-ci cible explicitement un
runtime **Ollama** et encapsule ses spécificités. Aucune ne remonte dans le
graphe LangGraph (`app.ai.agent.graph`) ni dans le code métier : le graphe
n'appelle que `LLMService`, qui n'appelle que l'interface `LLMProvider`.

Spécificités Ollama gérées ici (ou dans `OpenAICompatibleProvider` via ses
paramètres) :
- `base_url` : Ollama sert l'API compatible sous `.../v1` ; l'URL est
  normalisée pour tolérer une valeur avec ou sans `/v1` ;
- `api_key` : Ollama n'en exige pas, mais le SDK `openai` impose une valeur
  non vide → `"ollama"` par défaut (surchargée par `OLLAMA_API_KEY` si un
  proxy protège l'endpoint) ;
- `tool_choice` : NON supporté par l'endpoint `/v1` d'Ollama → jamais envoyé
  (`send_tool_choice=False`) ;
- `num_ctx` : la fenêtre de contexte par défaut d'Ollama (souvent 4096 tokens)
  peut être insuffisante pour le prompt système + l'historique + les extraits
  RAG. `OLLAMA_NUM_CTX` est transmis dans le corps de la requête ; les
  versions récentes d'Ollama l'honorent, sinon il faut le figer via un
  Modelfile (`PARAMETER num_ctx ...`) ;
- `tool_call.id` : la couche de compat d'Ollama en renvoie parfois des vides
  ou des doublons → régénérés dans `OpenAICompatibleProvider` (commun).
"""
from app.ai.exceptions import LLMProviderNotConfiguredError
from app.ai.providers._openai_compatible import OpenAICompatibleProvider
from app.core.config import settings


def _normalize_base_url(base_url: str) -> str:
    """Garantit un suffixe `/v1` (routes compatibles OpenAI d'Ollama)."""

    url = base_url.strip().rstrip("/")
    if not url.endswith("/v1"):
        url = f"{url}/v1"
    return url


class OllamaProvider(OpenAICompatibleProvider):
    """Fournisseur Ollama (local) via son endpoint compatible OpenAI."""

    def __init__(self) -> None:
        if not settings.OLLAMA_BASE_URL:
            raise LLMProviderNotConfiguredError("OLLAMA_BASE_URL is not configured")

        num_ctx = settings.OLLAMA_NUM_CTX
        default_body = {"num_ctx": num_ctx} if num_ctx and num_ctx > 0 else None

        super().__init__(
            api_key=settings.OLLAMA_API_KEY or "ollama",
            model=settings.OLLAMA_MODEL,
            base_url=_normalize_base_url(settings.OLLAMA_BASE_URL),
            default_body=default_body,
            send_tool_choice=False,
        )


__all__ = ["OllamaProvider"]
