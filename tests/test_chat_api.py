"""Tests HTTP de api/chat.py : séparation création / message, propriété, agent.

Contrat :
- POST /chat/conversations {"product_id": "..."}        → 201 (crée la conversation)
- POST /chat/message {"conversation_id": "...", "content": "..."} → 200

L'agent est remplacé par un `ScriptedLLMProvider` via `app.dependency_overrides`.
"""
import uuid

import pytest
import pytest_asyncio
from fastapi import Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

import uuid as _uuid

from app.ai.llm import LLMService
from app.ai.providers.base import LLMResult, ToolCall
from app.ai.rag.retriever import RetrievedChunk
from app.api.chat import get_chat_service
from app.core.dependencies import get_db_session
from app.main import app
from app.models.ticket import Ticket
from app.schemas.client_product import ClientProductItem
from app.schemas.user import UserCreate
from app.services.chat_service import ChatService
from app.services.client_product_service import ClientProductService
from app.services.user_service import UserService
from conftest import ScriptedLLMProvider, StubRetriever, unique_email

UNKNOWN = "00000000-0000-0000-0000-000000000000"


def _override_chat_service(script, *, chunks=None):
    async def _dep(db: AsyncSession = Depends(get_db_session)) -> ChatService:
        return ChatService(
            db,
            llm_service=LLMService(provider=ScriptedLLMProvider(script, text_reply="TITRE: Incident\n\nProblème\n--------\nPanne")),
            retriever=StubRetriever(chunks or []),
        )

    return _dep


def _set_script(script, *, chunks=None):
    app.dependency_overrides[get_chat_service] = _override_chat_service(script, chunks=chunks)


@pytest_asyncio.fixture(autouse=True)
async def default_agent():
    app.dependency_overrides[get_chat_service] = _override_chat_service(_DEFAULT_AGENT_SCRIPT)
    yield
    app.dependency_overrides.pop(get_chat_service, None)


@pytest_asyncio.fixture
async def chat_client(client, db_session, role_ids, product):
    """Un client (produit `product` affecté) + son token."""

    us = UserService(db_session)
    user = await us.create_user(
        UserCreate(email=unique_email("chatapi"), password="ValidPass1", role_id=role_ids["client"])
    )
    await ClientProductService(db_session).assign_products(
        user.id, [ClientProductItem(product_id=product.id, qte=1)]
    )
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "ValidPass1"})
    token = login.json()["access_token"]
    user_id = user.id

    yield user, token, product

    await db_session.execute(delete(Ticket).where(Ticket.client_id == user_id))
    await db_session.commit()
    row = await us.get_user_by_id(user_id)
    if row is not None:
        await db_session.delete(row)  # CASCADE conversations + client_products
        await db_session.commit()


def _h(token):
    return {"Authorization": f"Bearer {token}"}


async def _open_conv(client, token, product_id):
    resp = await client.post(
        "/api/v1/chat/conversations", json={"product_id": str(product_id)}, headers=_h(token)
    )
    return resp


# --- 401 -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoints_require_auth(client):
    assert (await client.post("/api/v1/chat/conversations", json={"product_id": UNKNOWN})).status_code == 401
    assert (await client.post("/api/v1/chat/message", json={"conversation_id": UNKNOWN, "content": "x"})).status_code == 401


# --- POST /chat/conversations -----------------------------------------


@pytest.mark.asyncio
async def test_open_conversation_ok(client, chat_client):
    _, token, product = chat_client
    resp = await _open_conv(client, token, product.id)

    assert resp.status_code == 201
    body = resp.json()
    assert body["product_id"] == str(product.id)
    assert body["pending_ticket_confirmation"] is False


@pytest.mark.asyncio
async def test_open_conversation_requires_product_id(client, chat_client):
    _, token, _ = chat_client
    resp = await client.post("/api/v1/chat/conversations", json={}, headers=_h(token))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_open_conversation_unknown_product_is_404(client, chat_client):
    _, token, _ = chat_client
    resp = await _open_conv(client, token, UNKNOWN)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_client_cannot_open_conversation_on_unassigned_product(client, chat_client, db_session):
    from app.models.product import Product

    _, token, _ = chat_client
    other = Product(reference=f"REF-{uuid.uuid4().hex[:8]}", name="Produit non affecté")
    db_session.add(other)
    await db_session.commit()
    other_id = other.id

    resp = await _open_conv(client, token, other_id)
    assert resp.status_code == 403

    await db_session.delete(await db_session.get(Product, other_id))
    await db_session.commit()


# --- POST /chat/message ---------------------------------------------


@pytest.mark.asyncio
async def test_send_message_requires_conversation_id(client, chat_client):
    _, token, _ = chat_client
    resp = await client.post("/api/v1/chat/message", json={"content": "Bonjour"}, headers=_h(token))
    assert resp.status_code == 422  # plus de création implicite de conversation


@pytest.mark.asyncio
async def test_send_message_in_own_conversation(client, chat_client):
    _, token, product = chat_client
    conv = (await _open_conv(client, token, product.id)).json()

    resp = await client.post(
        "/api/v1/chat/message",
        json={"conversation_id": conv["id"], "content": "Mon produit ne fonctionne plus"},
        headers=_h(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation_id"] == conv["id"]
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"] == "Réponse de l'agent."
    assert body["ticket_id"] is None


@pytest.mark.asyncio
async def test_send_message_unknown_conversation_is_404(client, chat_client):
    _, token, _ = chat_client
    resp = await client.post(
        "/api/v1/chat/message", json={"conversation_id": UNKNOWN, "content": "x"}, headers=_h(token)
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_client_cannot_send_message_in_another_users_conversation(client, chat_client, db_session, role_ids, product):
    _, token, _ = chat_client

    # une conversation appartenant à un AUTRE client
    us = UserService(db_session)
    other = await us.create_user(
        UserCreate(email=unique_email("otherclient"), password="ValidPass1", role_id=role_ids["client"])
    )
    await ClientProductService(db_session).assign_products(other.id, [ClientProductItem(product_id=product.id, qte=1)])
    other_login = await client.post("/api/v1/auth/login", json={"email": other.email, "password": "ValidPass1"})
    other_token = other_login.json()["access_token"]
    other_conv = (await _open_conv(client, other_token, product.id)).json()

    resp = await client.post(
        "/api/v1/chat/message",
        json={"conversation_id": other_conv["id"], "content": "je m'incruste"},
        headers=_h(token),
    )
    assert resp.status_code == 404  # jamais 200, jamais 403 révélateur

    await db_session.delete(await us.get_user_by_id(other.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_agent_ticket_creation_is_exposed_as_ticket_id(client, chat_client, db_session):
    user, token, product = chat_client
    conv = (await _open_conv(client, token, product.id)).json()

    # 1er message (diagnostic)
    await client.post(
        "/api/v1/chat/message",
        json={"conversation_id": conv["id"], "content": "Mon four ne s'allume plus"},
        headers=_h(token),
    )
    # 2e message : un diagnostic minimal (search_docs requis avant toute proposition
    # de ticket, cf. tools.request_ticket_creation) puis l'agent propose un ticket
    app.dependency_overrides[get_chat_service] = _override_chat_service(
        [
            LLMResult(tool_calls=(ToolCall("c0", "search_docs", {"query": "four ne s'allume plus"}),)),
            LLMResult(tool_calls=(ToolCall("c1", "request_ticket_creation", {"problem_summary": "four HS"}),)),
            LLMResult(text="Je propose un ticket. Confirmez-vous ?"),
        ]
    )
    r2 = await client.post(
        "/api/v1/chat/message",
        json={"conversation_id": conv["id"], "content": "Oui fusible vérifié, rien"},
        headers=_h(token),
    )
    assert r2.json()["ticket_id"] is None

    # 3e message : confirmation -> create_ticket
    app.dependency_overrides[get_chat_service] = _override_chat_service(
        [
            LLMResult(tool_calls=(ToolCall("c2", "create_ticket", {"description": "Four ne s'allume plus, fusible OK, non résolu."}),)),
            LLMResult(text="Ticket créé."),
        ]
    )
    r3 = await client.post(
        "/api/v1/chat/message",
        json={"conversation_id": conv["id"], "content": "Oui créez le ticket"},
        headers=_h(token),
    )
    assert r3.status_code == 200
    ticket_id = r3.json()["ticket_id"]
    assert ticket_id is not None

    ticket = await db_session.get(Ticket, uuid.UUID(ticket_id))
    assert ticket.client_id == user.id
    assert ticket.product_id == product.id
    assert ticket.conversation_id == uuid.UUID(conv["id"])


# --- Fournisseur LLM en échec (ex : Ollama indisponible) ----------


class _UnavailableProvider:
    """Simule un fournisseur injoignable (Ollama arrêté, modèle absent…) :
    `agenerate_tools` échoue comme le ferait `OllamaProvider` réel."""

    async def agenerate(self, messages, **kwargs):
        from app.ai.exceptions import LLMRequestError

        raise LLMRequestError("Connection refused (ollama)")

    async def agenerate_tools(self, messages, tools):
        from app.ai.exceptions import LLMRequestError

        raise LLMRequestError("Connection refused (ollama)")


def _override_with_unavailable_provider():
    async def _dep(db: AsyncSession = Depends(get_db_session)) -> ChatService:
        return ChatService(
            db,
            llm_service=LLMService(provider=_UnavailableProvider()),
            retriever=StubRetriever([]),
        )

    return _dep


@pytest.mark.asyncio
async def test_send_message_returns_503_when_llm_provider_unavailable(client, chat_client, db_session):
    """LLM_PROVIDER=ollama mais serveur injoignable : 503 propre, message
    client persisté, aucun message assistant orphelin, transaction saine."""

    from app.models.message import Message

    _, token, product = chat_client
    conv = (await _open_conv(client, token, product.id)).json()

    # (la fixture autouse `default_agent` restaure l'override au teardown)
    app.dependency_overrides[get_chat_service] = _override_with_unavailable_provider()
    resp = await client.post(
        "/api/v1/chat/message",
        json={"conversation_id": conv["id"], "content": "Mon produit ne démarre plus"},
        headers=_h(token),
    )

    assert resp.status_code == 503

    # le message client reste persisté ; aucun message assistant créé
    detail = await client.get(f"/api/v1/chat/conversations/{conv['id']}", headers=_h(token))
    roles = [m["role"] for m in detail.json()["messages"]]
    assert roles == ["user"], roles

    # la session de test reste utilisable (aucune transaction cassée)
    rows = (
        await db_session.execute(
            Message.__table__.select().where(Message.conversation_id == uuid.UUID(conv["id"]))
        )
    ).all()
    assert len(rows) == 1


# --- E2E : workflow de résolution interactive via l'API réelle ------


def _tc(name, **args):
    return ToolCall(f"c_{_uuid.uuid4().hex[:6]}", name, args)


# Script minimal satisfaisant le garde-fou backend B6 (search_docs puis
# submit_diagnosis obligatoires avant toute réponse finale, cf.
# `app.ai.agent.graph._gate_violation`) — sert de scénario "agent par défaut"
# pour les tests qui ne portent pas spécifiquement sur le diagnostic.
_DEFAULT_AGENT_SCRIPT = [
    LLMResult(tool_calls=(_tc("search_docs", query="diagnostic"),)),
    LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Cause générique", steps=["Vérifier le branchement"]),)),
    LLMResult(text="Réponse de l'agent."),
]


_CHUNK = RetrievedChunk(text="Vérifiez l'alimentation.", document_id=_uuid.uuid4(), title="Guide", category="faq", distance=0.1)


async def _post(client, token, conv_id, content):
    return await client.post(
        "/api/v1/chat/message", json={"conversation_id": conv_id, "content": content}, headers=_h(token)
    )


@pytest.mark.asyncio
async def test_e2e_branch_A_resolution_no_ticket(client, chat_client, db_session):
    _, token, product = chat_client
    conv = (await _open_conv(client, token, product.id)).json()

    _set_script(
        [
            LLMResult(tool_calls=(_tc("search_docs", query="E17"),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Bac papier", steps=["Retirer le bac", "Réinsérer"]),)),
            LLMResult(text="Cause : bac papier. 1. Retirez le bac 2. Réinsérez. Le problème persiste-t-il ?"),
        ],
        chunks=[_CHUNK],
    )
    r1 = await _post(client, token, conv["id"], "Mon imprimante affiche E17")
    assert r1.status_code == 200 and r1.json()["ticket_id"] is None

    _set_script(
        [
            LLMResult(tool_calls=(_tc("record_client_feedback", resolved=True),)),
            LLMResult(text="Parfait, ravi que ce soit réglé !"),
        ]
    )
    r2 = await _post(client, token, conv["id"], "c'est bon ça marche")
    assert r2.status_code == 200 and r2.json()["ticket_id"] is None

    from app.models.ticket import Ticket

    tickets = (await db_session.execute(Ticket.__table__.select().where(Ticket.conversation_id == _uuid.UUID(conv["id"])))).all()
    assert tickets == []


@pytest.mark.asyncio
async def test_e2e_branch_B_auto_escalation_creates_ticket(client, chat_client, db_session):
    user, token, product = chat_client
    conv = (await _open_conv(client, token, product.id)).json()

    # tour 1 : diagnostic
    _set_script(
        [
            LLMResult(tool_calls=(_tc("search_docs", query="ne démarre plus"),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Alimentation", steps=["Vérifier câble", "Tester prise"]),)),
            LLMResult(text="1. Vérifiez le câble 2. Testez une prise. Le problème persiste-t-il ?"),
        ],
        chunks=[_CHUNK],
    )
    await _post(client, token, conv["id"], "Mon four ne s'allume plus")

    # tour 2 : échec 1 + nouvelle tentative
    _set_script(
        [
            LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
            LLMResult(tool_calls=(_tc("search_docs", query="voyant éteint"),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Carte de puissance", steps=["Débrancher 30s", "Rebrancher"]),)),
            LLMResult(text="Nouvelle piste. Le problème persiste-t-il ?"),
        ],
        chunks=[_CHUNK],
    )
    r2 = await _post(client, token, conv["id"], "ça ne marche toujours pas")
    assert r2.json()["ticket_id"] is None

    # tour 3 : échec 2 == seuil -> escalade automatique
    _set_script(
        [
            LLMResult(tool_calls=(_tc("record_client_feedback", resolved=False),)),
            LLMResult(tool_calls=(_tc("escalate_to_technician", reason="Alimentation HS après 2 séries de vérifications"),)),
            LLMResult(text="Le problème persiste. Je crée un ticket pour un technicien."),
        ]
    )
    r3 = await _post(client, token, conv["id"], "toujours rien")
    assert r3.status_code == 200
    ticket_id = r3.json()["ticket_id"]
    assert ticket_id is not None

    from app.models.ticket import Ticket

    ticket = await db_session.get(Ticket, _uuid.UUID(ticket_id))
    assert ticket.client_id == user.id
    assert ticket.product_id == product.id
    assert ticket.conversation_id == _uuid.UUID(conv["id"])
    assert ticket.description.strip() and "toujours rien" not in ticket.description

    # nettoyage
    await db_session.execute(Ticket.__table__.delete().where(Ticket.id == ticket.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_e2e_multiple_issues_in_same_conversation_via_http(client, chat_client, db_session):
    """Point 4 (audit) — e2e HTTP : problème A résolu -> nouveau problème B
    dans la MÊME conversation (même product_id, aucune nouvelle conversation
    créée) -> nouveau diagnostic complet -> ticket propre à B."""

    user, token, product = chat_client
    conv = (await _open_conv(client, token, product.id)).json()

    # Problème A : diagnostic puis résolution.
    _set_script(
        [
            LLMResult(tool_calls=(_tc("search_docs", query="E17"),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Bac papier", steps=["Retirer le bac", "Réinsérer"]),)),
            LLMResult(text="Cause : bac papier. 1. Retirez 2. Réinsérez. Persiste-t-il ?"),
        ],
        chunks=[_CHUNK],
    )
    r1 = await _post(client, token, conv["id"], "Mon imprimante affiche E17")
    assert r1.status_code == 200 and r1.json()["ticket_id"] is None

    _set_script([LLMResult(tool_calls=(_tc("record_client_feedback", resolved=True),)), LLMResult(text="Réglé pour A.")])
    r2 = await _post(client, token, conv["id"], "c'est bon pour l'imprimante")
    assert r2.status_code == 200 and r2.json()["ticket_id"] is None

    # Problème B, distinct, dans la MÊME conversation.
    _set_script(
        [
            LLMResult(tool_calls=(_tc("start_new_issue", summary="voyant rouge clignote"),)),
            LLMResult(tool_calls=(_tc("search_docs", query="voyant rouge"),)),
            LLMResult(tool_calls=(_tc("submit_diagnosis", cause="Capot mal fermé", steps=["Ouvrir puis refermer le capot"]),)),
            LLMResult(text="Cause : capot mal fermé. Persiste-t-il ?"),
        ],
        chunks=[_CHUNK],
    )
    r3 = await _post(client, token, conv["id"], "maintenant le voyant rouge clignote")
    assert r3.status_code == 200
    body3 = r3.json()
    assert body3["conversation_id"] == conv["id"]  # toujours la même conversation
    assert body3["ticket_id"] is None
    assert "capot" in body3["message"]["content"].lower()

    # Le produit de la conversation n'a pas changé.
    detail = await client.get(f"/api/v1/chat/conversations/{conv['id']}", headers=_h(token))
    assert detail.json()["product_id"] == str(product.id)

    from app.models.conversation_event import ConversationEvent

    events = (
        await db_session.execute(
            ConversationEvent.__table__.select().where(ConversationEvent.conversation_id == _uuid.UUID(conv["id"]))
        )
    ).all()
    assert any(e.event_type == "new_issue" for e in events)
    assert sum(1 for e in events if e.event_type == "search") == 2  # historique des 2 cycles conservé


# --- GET / DELETE conversations (inchangés) -------------------------


@pytest.mark.asyncio
async def test_get_conversation_returns_history_and_product(client, chat_client):
    _, token, product = chat_client
    conv = (await _open_conv(client, token, product.id)).json()
    await client.post(
        "/api/v1/chat/message",
        json={"conversation_id": conv["id"], "content": "Question"},
        headers=_h(token),
    )

    resp = await client.get(f"/api/v1/chat/conversations/{conv['id']}", headers=_h(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["product_id"] == str(product.id)
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_delete_conversation(client, chat_client):
    _, token, product = chat_client
    conv = (await _open_conv(client, token, product.id)).json()

    assert (await client.delete(f"/api/v1/chat/conversations/{conv['id']}", headers=_h(token))).status_code == 204
    assert (await client.get(f"/api/v1/chat/conversations/{conv['id']}", headers=_h(token))).status_code == 404


__all__: list[str] = []
