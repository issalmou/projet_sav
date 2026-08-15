"""Script de démonstration du Diagnostic automatique (Semaine 8).

`DiagnosticService` n'a jamais eu de route API dédiée (décision actée dès la
Semaine 5 : aucune route publique n'existe pour l'appeler) — ce script
l'exerce directement, comme le fait déjà `tests/test_diagnostic_integration.py`.
Rien n'est inventé ici : c'est le même service, appelé de la même façon.

Deux modes :
- `--live` (par défaut) : utilise le vrai fournisseur LLM configuré (.env,
  LLM_PROVIDER) et le vrai RAG (ChromaDB réel). Résultat non scripté : le
  LLM décide lui-même RESOLU / EN_COURS / A_ESCALADER.
- `--deterministic` : rejoue une séquence de réponses fixes (même principe
  que tests/test_diagnostic_integration.py::test_full_workflow...), pour une
  démonstration reproductible garantie (ex: présentation critique/enregistrée).

Usage (depuis `backend/`) :
    PYTHONPATH=. python demo/demo_diagnostic.py --live
    PYTHONPATH=. python demo/demo_diagnostic.py --deterministic
"""
import argparse
import asyncio
import uuid

from app.ai.llm import LLMService
from app.ai.providers.base import LLMProvider, Message as LLMMessage
from app.database.session import AsyncSessionLocal
from app.schemas.user import UserCreate
from app.services.diagnostic_service import DiagnosticService
from app.services.ticket_service import TicketService
from app.services.user_service import UserService


class _ScriptedProvider(LLMProvider):
    """Rejoue une réponse différente à chaque appel (mode --deterministic)."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)

    async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
        return self._replies.pop(0)


# Ordre réel des appels LLM par tour (ChatService génère aussi un titre de
# conversation) : titre(Q1) -> diagnostic(Q1) -> titre affiné(Q1+Q2) -> diagnostic(Q2).
_DETERMINISTIC_REPLIES = [
    "Pompe à chaleur : code erreur",
    "Avez-vous vérifié le disjoncteur dédié et le niveau du fluide caloporteur ?\n[STATUT: EN_COURS]",
    "Pompe à chaleur : panne persistante",
    "Je ne trouve pas de solution dans la documentation disponible ; je transmets votre dossier à un technicien.\n[STATUT: A_ESCALADER]",
]


async def _get_or_create_demo_client(session) -> "User":  # noqa: F821 (type hint informatif)
    service = UserService(session)
    email = "demo.client@example.com"
    existing = await service.get_user_by_email(email)
    if existing is not None:
        return existing
    return await service.create_user(UserCreate(email=email, password="DemoPass1"))


async def run(live: bool) -> None:
    async with AsyncSessionLocal() as session:
        client = await _get_or_create_demo_client(session)

        llm_service = None if live else LLMService(provider=_ScriptedProvider(list(_DETERMINISTIC_REPLIES)))
        service = DiagnosticService(session, llm_service=llm_service)

        print(f"[1/2] Mode {'LIVE (vrai LLM)' if live else 'DETERMINISTIC (scripté)'}")
        print("Client :", "Ma pompe à chaleur affiche un code erreur et ne redémarre plus.")
        first = await service.diagnose(client, "Ma pompe à chaleur affiche un code erreur et ne redémarre plus.")
        print("Agent  :", first.message.content)
        print("Statut :", first.status.value)

        if first.status.value == "resolved":
            print("\n-> Résolu dès le premier échange, rien à escalader. Fin de la démonstration.")
            return

        print("\n[2/2] Client :", "J'ai vérifié, le problème persiste toujours.")
        second = await service.diagnose(
            client, "J'ai vérifié, le problème persiste toujours.", conversation_id=first.conversation.id
        )
        print("Agent  :", second.message.content)
        print("Statut :", second.status.value)

        if second.ticket is not None:
            persisted = await TicketService(session).get_ticket(second.ticket.id, client)
            print(f"\n-> Ticket créé : id={persisted.id} statut={persisted.status} titre='{persisted.title}'")
            print("   Consultable ensuite via l'API : GET /api/v1/tickets/{id} (en tant que staff).")
        else:
            print("\n-> Toujours en cours, aucune escalade sur ce tour (relancez le script pour continuer).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deterministic", action="store_true", help="Séquence de réponses fixes, reproductible.")
    args = parser.parse_args()
    asyncio.run(run(live=not args.deterministic))
