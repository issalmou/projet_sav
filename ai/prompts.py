"""Registre centralisé des prompts de l'agent IA SAV.

Aucun prompt ne doit être écrit en dur ailleurs (routes, services) : toute
formulation envoyée au LLM passe par ce module, pour rester cohérente et
facile à faire évoluer sans toucher à la couche métier.
"""
from app.ai.rag.retriever import RetrievedChunk

SYSTEM_PROMPT_SAV = """Tu es l'assistant IA du service après-vente (SAV) de la plateforme.
Tu aides les clients à :
- répondre aux questions fréquentes sur les produits ;
- diagnostiquer une panne à partir de sa description ;
- guider pas à pas vers une solution.

Consignes :
- Réponds de façon claire, concise et polie.
- Ne commence jamais ta réponse par une salutation (par exemple "Bonjour") : \
va directement au contenu de ta réponse.
- Si tu ne peux pas résoudre le problème avec certitude, dis-le clairement et \
propose au client de créer un ticket de support ou d'être mis en relation avec un technicien.
- N'invente jamais d'information sur un produit ou une procédure que tu ne connais pas."""

# Correspond à settings.SUPPORTED_LANGUAGES (core/config.py) et à User.preferred_language.
_LANGUAGE_NAMES = {"fr": "français", "en": "anglais", "ar": "arabe"}
_DEFAULT_LANGUAGE = "fr"


def build_system_prompt(preferred_language: str = _DEFAULT_LANGUAGE) -> str:
    """Retourne le prompt système, adapté à la langue préférée du client (exigence multilingue du CDC)."""

    language_name = _LANGUAGE_NAMES.get(preferred_language, _LANGUAGE_NAMES[_DEFAULT_LANGUAGE])
    return (
        f"{SYSTEM_PROMPT_SAV}\n\n"
        f"Réponds en {language_name}, sauf si le client écrit explicitement dans une autre langue."
    )


def build_title_prompt(preferred_language: str = _DEFAULT_LANGUAGE) -> str:
    """Prompt système pour résumer le premier message d'un client en un titre de conversation.

    Utilisé une seule fois, à la création d'une conversation, pour que
    l'historique du client (§9 du CDC) reste identifiable au premier coup
    d'œil plutôt que d'afficher un identifiant technique.
    """

    language_name = _LANGUAGE_NAMES.get(preferred_language, _LANGUAGE_NAMES[_DEFAULT_LANGUAGE])
    return (
        "Tu résumes la demande d'un client du support technique en un titre de conversation.\n\n"
        "Consignes strictes :\n"
        f"- Écris le titre en {language_name}.\n"
        "- 3 à 6 mots maximum, sans point final ni guillemets.\n"
        "- Résume le sujet concret de la demande (produit, panne, action demandée) : \
jamais une salutation générique comme \"Nouvelle conversation\" ou \"Question du client\".\n"
        "- Réponds uniquement avec le titre, sans aucune autre phrase autour."
    )


LOW_CONFIDENCE_INSTRUCTION = (
    "\n\nAucun document pertinent n'a été trouvé dans la base de connaissances pour cette question. "
    "Si tu ne connais pas le modèle exact du produit du client, demande-le-lui avant de répondre : "
    "cela permettra une recherche documentaire plus précise."
)

# Marqueurs machine-lisibles attendus en fin de réponse en mode diagnostic
# (cf. DIAGNOSTIC_STATUS_INSTRUCTION). Doivent rester synchronisés avec
# `DiagnosticService._STATUS_MARKER_PATTERN` / `app.utils.constants.DiagnosticStatus`.
DIAGNOSTIC_STATUS_MARKERS = {
    "RESOLU": "resolved",
    "EN_COURS": "in_progress",
    "A_ESCALADER": "escalate",
}

DIAGNOSTIC_STATUS_INSTRUCTION = (
    "\n\nTu es en mode diagnostic de panne (CDC : diagnostic automatique). "
    "Après avoir rédigé ta réponse, ajoute une toute dernière ligne, seule, contenant exactement "
    "l'un de ces marqueurs selon la situation :\n"
    "- [STATUT: RESOLU] si le problème du client est résolu, ou s'il s'agissait d'une simple question "
    "à laquelle tu as répondu complètement.\n"
    "- [STATUT: EN_COURS] si tu as besoin d'une information supplémentaire ou d'une vérification de la "
    "part du client avant de conclure.\n"
    "- [STATUT: A_ESCALADER] si, après vérification, tu ne parviens pas à résoudre le problème et qu'il "
    "faut créer un ticket de support et transférer le client à un technicien.\n\n"
    "Ne mentionne et n'explique jamais ce marqueur au client dans le texte de ta réponse : "
    "il doit apparaître seul, sur la toute dernière ligne."
)


def build_context_section(chunks: list[RetrievedChunk]) -> str:
    """Formate les chunks retrouvés par le RAG en section de contexte pour le prompt système.

    Chaîne vide si `chunks` est vide : le LLM répond alors sans contexte
    documentaire, uniquement sur ses instructions générales.
    """

    if not chunks:
        return ""

    formatted = "\n\n".join(f"[{chunk.title}]\n{chunk.text}" for chunk in chunks)
    return (
        "\n\nContexte documentaire pertinent (base de connaissances SAV) :\n"
        f"{formatted}\n\n"
        "Base ta réponse en priorité sur ce contexte. S'il ne suffit pas à répondre, dis-le clairement "
        "plutôt que d'inventer une information."
    )


__all__ = [
    "DIAGNOSTIC_STATUS_INSTRUCTION",
    "DIAGNOSTIC_STATUS_MARKERS",
    "LOW_CONFIDENCE_INSTRUCTION",
    "SYSTEM_PROMPT_SAV",
    "build_context_section",
    "build_system_prompt",
    "build_title_prompt",
]
