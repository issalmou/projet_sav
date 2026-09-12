"""Script de démonstration de l'agent SAV (LangGraph).

Parcours complet : client -> produit affecté -> conversation -> messages ->
agent (RAG + outils) -> proposition de ticket -> confirmation -> création.

Deux modes :
- `--live` (défaut) : vrai fournisseur LLM (.env, LLM_PROVIDER) + vrai RAG.
  L'agent décide lui-même quels outils appeler.
- `--deterministic` : fournisseur scripté (appels d'outils fixes), pour une
  démonstration reproductible.

Usage (depuis `backend/`) :
    PYTHONPATH=. python app/demo/demo_diagnostic.py --live
    PYTHONPATH=. python app/demo/demo_diagnostic.py --deterministic
"""
import argparse
import asyncio
import uuid

from sqlalchemy import select

from app.ai.llm import LLMService
from app.ai.providers.base import LLMProvider, LLMResult, ToolCall
from app.database.session import AsyncSessionLocal
from app.models.product import Product
from app.schemas.client_product import ClientProductItem
from app.schemas.user import UserCreate
from app.services.chat_service import ChatService
from app.services.client_product_service import ClientProductService
from app.services.user_service import UserService
from app.utils.constants import RoleName


class _ScriptedAgentProvider(LLMProvider):
    """Rejoue une séquence d'`LLMResult` (mode --deterministic)."""

    def __init__(self, script: list[LLMResult]) -> None:
        self._script = list(script)

    async def agenerate(self, messages, **kwargs) -> str:
        return "Pompe à chaleur : code erreur"

    async def agenerate_tools(self, messages, tools) -> LLMResult:
        return self._script.pop(0) if self._script else LLMResult(text="(fin de script)")


def _turn_1_script() -> list[LLMResult]:
    """Tour 1 : nouveau diagnostic complet — le garde-fou backend (B6) exige
    search_docs PUIS submit_diagnosis avant toute réponse finale, quel que
    soit ce que le LLM aurait spontanément fait."""

    return [
        LLMResult(tool_calls=(ToolCall("c1", "search_docs", {"query": "pompe à chaleur code erreur"}),)),
        LLMResult(
            tool_calls=(
                ToolCall(
                    "c1b",
                    "submit_diagnosis",
                    {
                        "cause": "Disjoncteur dédié déclenché ou niveau de fluide caloporteur bas",
                        "steps": ["Vérifier le disjoncteur dédié", "Contrôler le niveau de fluide caloporteur"],
                    },
                ),
            )
        ),
        LLMResult(text="Vérifiez le disjoncteur dédié et le niveau de fluide caloporteur, puis redémarrez. Le problème persiste-t-il ?"),
    ]


def _turn_2_script() -> list[LLMResult]:
    """Tour 2 : échec de la 1re tentative + demande explicite de ticket.

    Le seuil d'escalade automatique (2 tentatives, cf. settings) n'est pas
    encore atteint (1 seule tentative infructueuse) : le garde-fou B6 exige
    donc un NOUVEAU submit_diagnosis avant d'accepter toute réponse finale
    (record_client_feedback(resolved=false) ne suffit pas à lui seul à
    libérer la règle 3 du gate). request_ticket_creation (chemin explicite,
    indépendant du seuil d'escalade automatique) peut ensuite être proposé
    dans le même tour — la confirmation, elle, devra venir au tour suivant
    (B2 : jamais dans le même tour que la proposition)."""

    return [
        LLMResult(tool_calls=(ToolCall("c2", "record_client_feedback", {"resolved": False}),)),
        LLMResult(
            tool_calls=(
                ToolCall(
                    "c2b",
                    "submit_diagnosis",
                    {
                        "cause": "Pressostat ou fusible thermique défectueux",
                        "steps": ["Contrôler le pressostat", "Vérifier le fusible thermique"],
                    },
                ),
            )
        ),
        LLMResult(
            tool_calls=(
                ToolCall("c2c", "request_ticket_creation", {"problem_summary": "pompe à chaleur : panne persistante après 2 vérifications"}),
            )
        ),
        LLMResult(
            text=(
                "Essayez maintenant de contrôler le pressostat et le fusible thermique. Si le "
                "problème persiste malgré cette nouvelle vérification, souhaitez-vous que je crée "
                "un ticket pour qu'un technicien intervienne ? (oui / non)"
            )
        ),
    ]


def _turn_3_script() -> list[LLMResult]:
    """Tour 3 : confirmation du client, un tour APRÈS la proposition (B2).

    Un diagnostic était de nouveau en attente de retour (2e submit_diagnosis
    du tour précédent) : record_client_feedback est donc à nouveau
    obligatoire (règle 1 du gate) avant create_ticket."""

    return [
        LLMResult(tool_calls=(ToolCall("c3", "record_client_feedback", {"resolved": False}),)),
        LLMResult(
            tool_calls=(
                ToolCall(
                    "c3b",
                    "create_ticket",
                    {
                        "description": (
                            "Pompe à chaleur en panne, code erreur ; disjoncteur, fluide, pressostat "
                            "et fusible thermique vérifiés ; non résolu, intervention technique nécessaire."
                        ),
                    },
                ),
            )
        ),
        LLMResult(text="Votre ticket a été créé et transmis à un technicien. Vous serez recontacté."),
    ]


async def _setup(session):
    us = UserService(session)
    client = await us.get_user_by_email("demo.client@example.com")
    if client is None:
        from app.services.role_service import RoleService

        role = await RoleService(session).get_role_by_name(RoleName.CLIENT.value)
        client = await us.create_user(
            UserCreate(email="demo.client@example.com", password="DemoPass1", role_id=role.id if role else None)
        )

    # Bug corrigé (audit) : `Product.__table__.select().limit(1)` piochait une
    # ligne PRODUIT QUELCONQUE (ex. laissée par une suite de tests e2e) et
    # lisait à tort sa 1re colonne comme un id — ce produit démo est
    # maintenant identifié explicitement par son nom, jamais par une ligne
    # arbitraire de la table.
    result = await session.execute(select(Product).where(Product.name == "Pompe à chaleur Demo").limit(1))
    product = result.scalar_one_or_none()
    if product is None:
        product = Product(reference=f"DEMO-{uuid.uuid4().hex[:6]}", name="Pompe à chaleur Demo", warranty_months=24)
        session.add(product)
        await session.commit()
        await session.refresh(product)

    await ClientProductService(session).assign_products(
        client.id, [ClientProductItem(product_id=product.id, qte=1)]
    )
    return client, product


async def run(live: bool) -> None:
    async with AsyncSessionLocal() as session:
        client, product = await _setup(session)
        print(f"Mode {'LIVE' if live else 'DETERMINISTIC'} | produit : {product.name} ({product.reference})")

        def svc(script):
            llm = None if live else LLMService(provider=_ScriptedAgentProvider(script))
            return ChatService(session, llm_service=llm)

        conversation = await svc([]).open_conversation(client, product.id)
        print(f"Conversation ouverte : {conversation.id}\n")

        msgs = [
            ("Ma pompe à chaleur affiche un code erreur et ne redémarre plus.", _turn_1_script()),
            ("J'ai vérifié le disjoncteur et le fluide, le problème persiste.", _turn_2_script()),
            ("Oui, créez un ticket s'il vous plaît.", _turn_3_script()),
        ]
        for text, script in msgs:
            print("Client :", text)
            result = await svc(script).handle_message(client, conversation.id, text)
            print("Agent  :", result.message.content)
            if result.ticket_id:
                print(f"\n-> Ticket créé : {result.ticket_id}")
                break
            print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deterministic", action="store_true", help="Appels d'outils scriptés, reproductible.")
    args = parser.parse_args()
    asyncio.run(run(live=not args.deterministic))
