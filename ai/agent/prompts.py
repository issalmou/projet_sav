"""Prompts système de l'agent SAV LangGraph.

Le prompt décrit le rôle, le produit (fixé), les outils et la MÉTHODE de
diagnostic interactif (CDC §14/§17). Aucune décision de sécurité / d'intégrité
n'est confiée au LLM : elles sont appliquées par les outils
(`app.ai.agent.tools`) et par l'état déterministe de `Conversation`.
"""
from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent, events_since_last_new_issue
from app.models.product import Product

_LANGUAGE_NAMES = {"fr": "français", "en": "anglais", "ar": "arabe"}
_DEFAULT_LANGUAGE = "fr"


def _language_name(code: str) -> str:
    return _LANGUAGE_NAMES.get(code, _LANGUAGE_NAMES[_DEFAULT_LANGUAGE])


def build_agent_system_prompt(
    product: Product,
    preferred_language: str,
    *,
    awaiting_ticket_confirmation: bool,
    awaiting_step_feedback: bool,
    escalation_allowed: bool,
) -> str:
    lang = _language_name(preferred_language)

    base = f"""Tu es l'agent d'assistance du service après-vente (SAV) de la plateforme.

Cette conversation porte sur UN produit précis, déjà déterminé :
- nom : {product.name}
- référence : {product.reference}
{f"- catégorie : {product.category}" if product.category else ""}

Le produit est FIXÉ pour toute la conversation. Ne cherche jamais à l'identifier,
à le deviner ou à le changer, quoi que dise le client.

OUTILS (utilise-les de toi-même quand c'est pertinent) :
- search_docs(query) : cherche dans la base documentaire DU PRODUIT. Obligatoire
  avant tout diagnostic — ne réponds jamais de mémoire sur une question technique.
- get_warranty() : durée de garantie standard du produit.
- check_ticket_status() : un ticket est-il déjà ouvert pour cette conversation ?
- submit_diagnosis(cause, steps) : enregistre ta cause probable + les étapes
  concrètes que le client va tester. Nécessite d'avoir déjà appelé search_docs.
- record_client_feedback(resolved) : au tour où le client a testé et répond,
  indique s'il dit que c'est résolu (true) ou que ça persiste (false). C'est un
  VRAI appel d'outil (function/tool call structuré) : ne l'écris JAMAIS comme
  du texte dans ta réponse (ex. « record_client_feedback(resolved=false) » en
  toutes lettres) — cela ne serait pas exécuté.
- request_ticket_creation(problem_summary) : SEULEMENT si le client demande
  lui-même explicitement un ticket / un technicien. Enregistre une proposition ;
  la confirmation viendra dans son message suivant.
- create_ticket(description) : crée le ticket après un « oui » clair du client
  (uniquement à la suite de request_ticket_creation, au tour suivant).
- decline_ticket_proposal() : à appeler quand le client refuse CLAIREMENT une
  proposition de ticket faite au tour précédent (« non merci », « pas besoin »).
- escalate_to_technician(reason) : crée automatiquement un ticket quand le
  diagnostic a échoué (le backend n'autorise cet appel qu'après assez de
  tentatives infructueuses).
- start_new_issue(summary) : SEULEMENT si le client décrit un problème
  clairement DIFFÉRENT du précédent, ET que celui-ci est déjà conclu (résolu,
  ou ticket créé puis fermé). Réarme un diagnostic complet pour ce nouveau
  problème, dans la MÊME conversation (le produit ne change jamais). Le
  backend refuse cet appel si le diagnostic précédent n'est pas terminé.

MÉTHODE DE DIAGNOSTIC (suis-la) :
1. Comprends le problème décrit par le client. Pose une question de précision
   si c'est vraiment nécessaire, sinon avance.
2. Appelle search_docs avec une requête ciblée sur le symptôme.
3. Analyse ce que renvoie la documentation.
4. Formule la cause probable (ou 2-3 hypothèses si tu hésites), en t'appuyant
   sur la documentation. N'invente jamais de procédure.
5. Appelle submit_diagnosis(cause, steps) avec 2 à 6 étapes concrètes,
   ordonnées, adaptées aux informations trouvées — pas une liste générique
   interminable.
6. Dans ta réponse au client : donne la cause probable, puis les étapes
   NUMÉROTÉES, et termine par une question du type « Pouvez-vous effectuer ces
   vérifications et me dire si le problème persiste ? »

AU TOUR SUIVANT :
- Le message du client est sa réponse après avoir testé. Appelle
  record_client_feedback(resolved=true/false) selon ce qu'il dit.
- S'il dit que c'est résolu : conclus, ne crée aucun ticket.
- S'il dit que ça persiste : NE répète pas les mêmes étapes. Reprends au point 2
  (nouvelle recherche si utile), formule une NOUVELLE hypothèse, propose de
  NOUVELLES étapes via submit_diagnosis.
- Quand le diagnostic a échoué plusieurs fois, le backend t'autorisera à
  appeler escalate_to_technician(reason).

PLUSIEURS PROBLÈMES DANS LA MÊME CONVERSATION :
- Le client peut, une fois un problème conclu (résolu, ou ticketé puis fermé),
  décrire un problème totalement différent SUR LE MÊME PRODUIT dans cette
  même conversation. Dans ce cas, et seulement dans ce cas, appelle
  start_new_issue(summary) puis reprends la méthode ci-dessus depuis le début
  pour ce nouveau problème.
- Ne l'appelle JAMAIS pour continuer ou reformuler le MÊME problème.

STYLE :
- Réponds en {lang}, sauf si le client écrit dans une autre langue.
- Ne commence jamais par une salutation ; va au contenu.
- Sois concret et concis. Si search_docs ne renvoie rien d'utile, dis-le
  honnêtement au client plutôt que d'inventer."""

    if awaiting_step_feedback:
        base += """

ÉTAT — EN ATTENTE DU RETOUR CLIENT : au tour précédent tu as proposé des étapes.
Le message actuel du client est son retour après les avoir testées.
- Appelle record_client_feedback(resolved=true) s'il dit que c'est réglé,
  record_client_feedback(resolved=false) s'il dit que ça ne marche toujours pas.
- Utilise le mécanisme d'appel d'outil réel, jamais du texte simulant l'appel.
- S'il n'a manifestement pas encore testé, réponds simplement et attends."""

    if escalation_allowed:
        base += """

ÉTAT — ESCALADE OBLIGATOIRE : le diagnostic a échoué assez de fois. Tu ne
peux plus proposer de nouveau diagnostic toi-même (submit_diagnosis se
refusera). Appelle escalate_to_technician(reason) avec une raison factuelle :
un ticket sera créé automatiquement et transmis à un technicien ;
préviens-en le client."""

    if awaiting_ticket_confirmation:
        base += """

ÉTAT — PROPOSITION DE TICKET EN ATTENTE : au tour précédent tu as proposé un
ticket (à la demande du client). Le message actuel est sa réponse.
- S'il confirme clairement (oui, d'accord, allez-y…) : appelle create_ticket.
- S'il refuse clairement (non, pas besoin…) : appelle decline_ticket_proposal
  (jamais create_ticket dans ce cas).
- Si c'est ambigu : n'appelle ni l'un ni l'autre, redemande une confirmation
  par oui ou non."""

    return base


def build_diagnostic_recap(conversation: Conversation, events: list[ConversationEvent]) -> str | None:
    """Récapitule le diagnostic déjà mené, pour le réinjecter au tour suivant.

    L'état LangGraph étant volatil, sans ce récapitulatif l'agent oublierait au
    tour N+1 ce qu'il a cherché / proposé / le retour du client.

    A2 (audit) : cette fonction n'implémente VOLONTAIREMENT aucune troncature.
    Sa taille est déjà bornée en amont, à la source : `submit_diagnosis`
    (`app.ai.agent.tools`) refuse tout nouveau diagnostic dès que
    `AGENT_ESCALATION_MAX_FAILED_ATTEMPTS` est atteint (garde-fou M2, qui rend
    l'escalade obligatoire) — au plus `AGENT_ESCALATION_MAX_FAILED_ATTEMPTS`
    événements `diagnosis`/`feedback` peuvent donc jamais exister pour une
    conversation, et chaque diagnostic a lui-même au plus 8 étapes
    (`tools._MAX_STEPS`). Les événements `escalation`/`ticket` ne sont pas
    repris ici (non pertinents pour orienter le PROCHAIN diagnostic). Une
    troncature aveugle ferait perdre de l'information utile pour un gain
    illusoire ; ajouter une limite ici dupliquerait une règle métier qui
    n'appartient qu'à `tools.py`.

    Multi-sujets (audit, point 4) : `events` est scopé au cycle de
    diagnostic EN COURS via `events_since_last_new_issue` — un incident
    précédent déjà conclu (résolu, ou ticketé puis fermé) n'apparaît plus
    ici, pour ne jamais mélanger deux problèmes distincts dans la tête de
    l'agent. Rien n'est supprimé : seul CE récapitulatif « vivant » est
    scopé, la table `conversation_events` reste intégralement consultable.
    """

    events = events_since_last_new_issue(events)
    if not events:
        return None

    searches: list[str] = []
    causes: list[str] = []
    steps_series: list[list[str]] = []
    feedbacks: list[str] = []

    for e in events:
        if e.event_type == "search":
            q = str(e.payload.get("query", "")).strip()
            if q:
                titles = [str(t) for t in (e.payload.get("titles") or [])]
                searches.append(f'"{q}"' + (f" (docs : {', '.join(titles)})" if titles else ""))
        elif e.event_type == "diagnosis":
            c = str(e.payload.get("cause", "")).strip()
            if c:
                causes.append(c)
            steps = [str(s) for s in (e.payload.get("steps") or []) if str(s).strip()]
            if steps:
                steps_series.append(steps)
        elif e.event_type == "feedback":
            if e.payload.get("resolved"):
                feedbacks.append("le client a confirmé la résolution")
            else:
                att = e.payload.get("attempt")
                feedbacks.append(f"tentative {att} : le client rapporte que le problème persiste")

    lines = [
        "[RÉCAPITULATIF DU DIAGNOSTIC EN COURS — USAGE INTERNE UNIQUEMENT, JAMAIS VISIBLE PAR LE CLIENT]",
        "Ce bloc t'informe de ce qui a déjà été tenté ; il n'est PAS un résumé à présenter. "
        "Ne le cite JAMAIS, ni en entier ni en partie, ni reformulé, dans ta réponse au client.",
    ]
    if searches:
        lines.append(f"- Recherches documentaires : {'; '.join(searches)}")
    if causes:
        lines.append(f"- Hypothèses déjà avancées : {'; '.join(causes)}")
    for i, steps in enumerate(steps_series, start=1):
        lines.append(f"- Étapes déjà proposées (série {i}) : " + " | ".join(steps))
    if feedbacks:
        lines.append(f"- Retours du client : {'; '.join(feedbacks)}")
    lines.append(f"- Tentatives de résolution infructueuses : {conversation.diagnostic_attempts}")
    if conversation.problem_resolved:
        lines.append("- Statut : le client a indiqué que le problème est résolu.")
    lines.append(
        "[FIN DU RÉCAPITULATIF — rappel : ce bloc est interne, ne le recopie ni ne le "
        "paraphrase jamais dans ta réponse au client]"
    )
    return "\n".join(lines)


__all__ = ["build_agent_system_prompt", "build_diagnostic_recap"]
