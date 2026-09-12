"""Tests du modèle ConversationEvent et de l'état de diagnostic sur Conversation."""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent, events_since_last_new_issue
from app.schemas.user import UserCreate
from app.services.user_service import UserService


@pytest_asyncio.fixture
async def chat_user(db_session):
    service = UserService(db_session)
    user = await service.create_user(
        UserCreate(email=f"cevt.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1")
    )
    user_id = user.id
    yield user
    still_there = await service.get_user_by_id(user_id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


@pytest.mark.asyncio
async def test_conversation_defaults_for_diagnostic_state(db_session, chat_user, product_id):
    conv = Conversation(user_id=chat_user.id, product_id=product_id)
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    assert conv.diagnostic_attempts == 0
    assert conv.search_performed is False
    assert conv.awaiting_step_feedback is False
    assert conv.problem_resolved is False

    await db_session.delete(conv)
    await db_session.commit()


@pytest.mark.asyncio
async def test_conversation_events_persist_and_cascade(db_session, chat_user, product_id):
    conv = Conversation(user_id=chat_user.id, product_id=product_id)
    db_session.add(conv)
    await db_session.flush()

    db_session.add_all(
        [
            ConversationEvent(conversation_id=conv.id, event_type="search", payload={"query": "E17", "titles": ["Guide"]}),
            ConversationEvent(conversation_id=conv.id, event_type="diagnosis", payload={"cause": "bac", "steps": ["a", "b"]}),
            ConversationEvent(conversation_id=conv.id, event_type="feedback", payload={"resolved": False, "attempt": 1}),
        ]
    )
    await db_session.commit()
    conv_id = conv.id

    rows = (
        await db_session.execute(
            select(ConversationEvent).where(ConversationEvent.conversation_id == conv_id).order_by(ConversationEvent.created_at)
        )
    ).scalars().all()
    assert [r.event_type for r in rows] == ["search", "diagnosis", "feedback"]
    assert rows[1].payload["steps"] == ["a", "b"]

    # suppression de la conversation -> cascade DB sur les événements
    await db_session.delete(await db_session.get(Conversation, conv_id))
    await db_session.commit()
    remaining = (
        await db_session.execute(select(ConversationEvent).where(ConversationEvent.conversation_id == conv_id))
    ).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_conversation_event_type_check_constraint(db_session, chat_user, product_id):
    conv = Conversation(user_id=chat_user.id, product_id=product_id)
    db_session.add(conv)
    await db_session.flush()

    db_session.add(ConversationEvent(conversation_id=conv.id, event_type="not_a_valid_type", payload={}))
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.commit()
    await db_session.rollback()

    await db_session.execute(select(Conversation))  # session réutilisable
    still = await db_session.get(Conversation, conv.id)
    if still is not None:
        await db_session.delete(still)
        await db_session.commit()


@pytest.mark.asyncio
async def test_new_issue_is_a_valid_event_type(db_session, chat_user, product_id):
    """Audit point 4 : la contrainte CHECK autorise désormais 'new_issue'
    (migration b7e2f4a1c9d6), sans régression sur les types existants."""

    conv = Conversation(user_id=chat_user.id, product_id=product_id)
    db_session.add(conv)
    await db_session.flush()

    db_session.add(ConversationEvent(conversation_id=conv.id, event_type="new_issue", payload={"summary": "écran"}))
    await db_session.commit()  # ne doit PAS lever

    await db_session.delete(await db_session.get(Conversation, conv.id))
    await db_session.commit()


def _event(event_type: str, payload: dict) -> ConversationEvent:
    return ConversationEvent(conversation_id=uuid.uuid4(), event_type=event_type, payload=payload)


def test_events_since_last_new_issue_returns_all_when_no_boundary():
    events = [_event("search", {}), _event("diagnosis", {}), _event("feedback", {})]
    assert events_since_last_new_issue(events) == events


def test_events_since_last_new_issue_scopes_to_latest_cycle():
    e_search_a = _event("search", {"query": "A"})
    e_diag_a = _event("diagnosis", {"cause": "A"})
    e_boundary = _event("new_issue", {"summary": "B"})
    e_search_b = _event("search", {"query": "B"})
    e_diag_b = _event("diagnosis", {"cause": "B"})

    scoped = events_since_last_new_issue([e_search_a, e_diag_a, e_boundary, e_search_b, e_diag_b])

    assert scoped == [e_search_b, e_diag_b]


def test_events_since_last_new_issue_uses_the_latest_boundary_only():
    """Plusieurs cycles successifs : seul le tout dernier compte pour la
    lecture 'vivante' — les cycles antérieurs restent dans la table mais
    hors du scope courant."""

    e_a = _event("diagnosis", {"cause": "A"})
    boundary1 = _event("new_issue", {"summary": "B"})
    e_b = _event("diagnosis", {"cause": "B"})
    boundary2 = _event("new_issue", {"summary": "C"})
    e_c = _event("diagnosis", {"cause": "C"})

    scoped = events_since_last_new_issue([e_a, boundary1, e_b, boundary2, e_c])

    assert scoped == [e_c]


def test_events_since_last_new_issue_empty_after_boundary_with_no_events_yet():
    boundary = _event("new_issue", {"summary": "B"})
    assert events_since_last_new_issue([boundary]) == []


__all__: list[str] = []
