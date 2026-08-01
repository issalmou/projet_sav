"""Service LLM : point d'entrée unique de la couche IA pour le reste de l'app.

`ChatService` (couche métier) n'appelle que `LLMService` — jamais un provider
concret ni `LLMProviderFactory` directement. Ce service reste volontairement
indépendant de FastAPI : il ne lève que des exceptions de `app.ai.exceptions`,
charge à l'appelant (route ou service métier) de les traduire si besoin.
"""
from app.ai.exceptions import LLMError, LLMRequestError
from app.ai.prompts import build_title_prompt
from app.ai.providers.base import LLMProvider, Message
from app.ai.providers.factory import LLMProviderFactory

# Longueur maximale d'un titre de conversation généré (cohérent avec l'usage
# affiché en liste ; la colonne DB (String(200)) laisse largement la marge).
TITLE_MAX_LENGTH = 60


class LLMService:
    """Envoie des messages au fournisseur LLM actif et retourne sa réponse."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        # `provider` est injectable pour les tests (fournisseur factice) ;
        # par défaut, le fournisseur actif est résolu via LLM_PROVIDER (.env).
        self._provider = provider or LLMProviderFactory.create()

    async def generate_reply(self, messages: list[Message]) -> str:
        """Envoie l'historique de messages au LLM et retourne sa réponse texte."""

        if not messages:
            raise LLMError("Cannot generate a reply from an empty message list")

        return await self._provider.agenerate(messages)

    async def generate_title(self, message: str, preferred_language: str = "fr") -> str:
        """Résume `message` en un titre court et compréhensible, dans la langue du client.

        Lève `LLMRequestError` si le fournisseur ne renvoie rien d'exploitable
        (réponse vide une fois nettoyée), pour que l'appelant puisse retomber
        sur un titre de secours plutôt que d'afficher un titre vide.
        """

        llm_messages: list[Message] = [
            {"role": "system", "content": build_title_prompt(preferred_language)},
            {"role": "user", "content": message},
        ]
        raw_title = await self._provider.agenerate(llm_messages)
        title = _clean_title(raw_title)

        if not title:
            raise LLMRequestError("Le fournisseur LLM n'a renvoyé aucun titre exploitable")

        return title


def _clean_title(raw_title: str, *, max_length: int = TITLE_MAX_LENGTH) -> str:
    """Nettoie la réponse brute du LLM pour n'en garder qu'un titre lisible.

    Retire les guillemets/espaces superflus qu'un LLM ajoute parfois autour de
    sa réponse et tronque au dernier mot entier si le titre dépasse `max_length`,
    pour ne jamais couper un mot en plein milieu.
    """

    title = raw_title.strip().strip("\"'«»").strip().rstrip(".!")

    if len(title) <= max_length:
        return title

    truncated = title[:max_length].rsplit(" ", 1)[0].rstrip(".,;:!?")
    return f"{truncated}…" if truncated else title[:max_length]


__all__ = ["LLMService", "TITLE_MAX_LENGTH"]
