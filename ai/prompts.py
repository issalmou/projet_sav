"""Prompts partagés de la couche IA hors agent.

Depuis le passage à l'agent LangGraph (`app.ai.agent`), le prompt système du
dialogue et la boucle d'outils vivent dans `app.ai.agent.prompts`. Ce module
ne conserve que le prompt de génération de titre de conversation, utilisé par
`LLMService.generate_title` (indépendant de l'agent).
"""
_LANGUAGE_NAMES = {"fr": "français", "en": "anglais", "ar": "arabe"}
_DEFAULT_LANGUAGE = "fr"


def build_title_prompt(preferred_language: str = _DEFAULT_LANGUAGE) -> str:
    """Prompt système pour résumer le premier message d'un client en un titre de conversation."""

    language_name = _LANGUAGE_NAMES.get(preferred_language, _LANGUAGE_NAMES[_DEFAULT_LANGUAGE])
    return (
        "Tu résumes la demande d'un client du support technique en un titre de conversation.\n\n"
        "Consignes strictes :\n"
        f"- Écris le titre en {language_name}.\n"
        "- 3 à 6 mots maximum, sans point final ni guillemets.\n"
        "- Résume le sujet concret de la demande (produit, panne, action demandée) : "
        'jamais une salutation générique comme "Nouvelle conversation" ou "Question du client".\n'
        "- Réponds uniquement avec le titre, sans aucune autre phrase autour."
    )


__all__ = ["build_title_prompt"]
