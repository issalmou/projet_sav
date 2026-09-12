"""Script de démonstration de l'agent SAV (LangGraph).

Parcours complet : client -> produit affecté -> conversation -> messages ->
agent (RAG + outils) -> proposition de ticket -> confirmation -> création.

Deux modes :
- `--live` (défaut) : vrai fournisseur LLM (.env, LLM_PROVIDER) + vrai RAG.
  L'agent décide lui-même quels outils appeler.
- `--deterministic` : fournisseur scripté (appels d'outils fixes), pour une
  démonstration reproductible.

Usage (depuis `backend/`) :
    PYTHONPATH=. python demo/demo_diagnostic.py --live
    PYTHONPATH=. python demo/demo_diagnostic.py --deterministic
"""
import argparse
import asyncio
import uuid

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
    return [
        LLMResult(tool_calls=(ToolCall("c1", "search_docs", {"query": "pompe à chaleur code erreur"}),)),
        LLMResult(text="Vérifiez le disjoncteur dédié et le niveau de fluide caloporteur, puis redémarrez."),
    ]


def _turn_2_script() -> list[LLMResult]:
    return [
        LLMResult(tool_calls=(ToolCall("c2", "request_ticket_creation", {"problem_summary": "pompe à chaleur : panne persistante après vérifications"}),)),
        LLMResult(text="Je n'ai pas pu résoudre le problème. Souhaitez-vous que je crée un ticket de support ? (oui / non)"),
    ]


def _turn_3_script() -> list[LLMResult]:
    return [
        LLMResult(tool_calls=(ToolCall("c3", "create_ticket", {"description": "Pompe à chaleur en panne, code erreur ; disjoncteur et fluide vérifiés ; non résolu, intervention technique nécessaire."}),)),
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

    result = await session.execute(Product.__table__.select().limit(1))
    row = result.first()
    if row is None:
        product = Product(reference=f"DEMO-{uuid.uuid4().hex[:6]}", name="Pompe à chaleur Demo", warranty_months=24)
        session.add(product)
        await session.commit()
        await session.refresh(product)
    else:
        product = await session.get(Product, row[0])

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
