"""Tests de ChatService.send_message : orchestration complète (tâche 3.8)."""
import uuid

import pytest
import pytest_asyncio

from app.ai.exceptions import LLMRequestError
from app.ai.llm import LLMService
from app.ai.providers.base import LLMProvider, Message as LLMMessage
from app.schemas.user import UserCreate
from app.services.chat_service import ChatService
from app.services.user_service import UserService


class FakeProvider(LLMProvider):
    """Fournisseur factice : rejoue une réponse fixe, sans appel réseau."""

    def __init__(self, reply: str = "Réponse factice") -> None:
        self.reply = reply
        self.received_messages: list[LLMMessage] | None = None
        self.call_count = 0

    async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
        self.call_count += 1
        self.received_messages = messages
        return self.reply


class SequencedProvider(LLMProvider):
    """Fournisseur factice qui rejoue une réponse différente à chaque appel.

    Sert à distinguer, dans un même `send_message`, la réponse du titre
    (1er appel) de la réponse du chat (2e appel).
    """

    def __init__(self, replies: list[str | Exception]) -> None:
        self.replies = list(replies)
        self.received_messages_per_call: list[list[LLMMessage]] = []

    async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
        self.received_messages_per_call.append(messages)
        outcome = self.replies.pop(0)

        if isinstance(outcome, Exception):
            raise outcome

        return outcome


@pytest_asyncio.fixture
async def chat_user(db_session):
    service = UserService(db_session)
    email = f"chat.{uuid.uuid4().hex[:10]}@example.com"
    user = await service.create_user(UserCreate(email=email, password="ValidPass1"))
    user_id = user.id  # capturé avant le test : un rollback() y expirerait `user`

    yield user

    still_there = await service.get_user_by_id(user_id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


@pytest.mark.asyncio
async def test_send_message_creates_conversation_when_none_given(db_session, chat_user):
    fake_provider = FakeProvider(reply="Bonjour, comment puis-je vous aider ?")
    chat_service = ChatService(db_session, llm_service=LLMService(provider=fake_provider))

    conversation, assistant_message = await chat_service.send_message(chat_user, "Bonjour")

    assert conversation.user_id == chat_user.id
    assert assistant_message.role == "assistant"
    assert assistant_message.content == "Bonjour, comment puis-je vous aider ?"


@pytest.mark.asyncio
async def test_send_message_persists_user_and_assistant_messages(db_session, chat_user):
    fake_provider = FakeProvider(reply="ok")
    chat_service = ChatService(db_session, llm_service=LLMService(provider=fake_provider))

    conversation, _ = await chat_service.send_message(chat_user, "Mon imprimante affiche E17")

    history = await chat_service.get_history(conversation.id, chat_user.id)

    assert [message.role for message in history] == ["user", "assistant"]
    assert history[0].content == "Mon imprimante affiche E17"
    assert history[1].content == "ok"


@pytest.mark.asyncio
async def test_send_message_reuses_existing_conversation_and_sends_full_history(db_session, chat_user):
    fake_provider = FakeProvider(reply="deuxième réponse")
    chat_service = ChatService(db_session, llm_service=LLMService(provider=fake_provider))

    conversation, _ = await chat_service.send_message(chat_user, "premier message")
    conversation_again, assistant_message = await chat_service.send_message(
        chat_user, "deuxième message", conversation_id=conversation.id
    )

    assert conversation_again.id == conversation.id
    assert assistant_message.content == "deuxième réponse"

    # Le LLM doit recevoir tout l'historique (system + 3 messages précédents) au 2e appel.
    assert fake_provider.received_messages is not None
    roles = [message["role"] for message in fake_provider.received_messages]
    assert roles == ["system", "user", "assistant", "user"]


@pytest.mark.asyncio
async def test_send_message_includes_system_prompt_first(db_session, chat_user):
    fake_provider = FakeProvider()
    chat_service = ChatService(db_session, llm_service=LLMService(provider=fake_provider))

    await chat_service.send_message(chat_user, "Bonjour")

    assert fake_provider.received_messages is not None
    assert fake_provider.received_messages[0]["role"] == "system"


@pytest.mark.asyncio
async def test_send_message_to_another_users_conversation_raises_value_error(db_session, chat_user):
    service = UserService(db_session)
    other_user = await service.create_user(
        UserCreate(email=f"other.{uuid.uuid4().hex[:10]}@example.com", password="ValidPass1")
    )

    chat_service = ChatService(db_session, llm_service=LLMService(provider=FakeProvider()))
    conversation, _ = await chat_service.send_message(other_user, "Bonjour")

    with pytest.raises(ValueError):
        await chat_service.send_message(chat_user, "Bonjour", conversation_id=conversation.id)

    await db_session.delete(other_user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_send_message_sets_llm_generated_title_on_new_conversation(db_session, chat_user):
    provider = SequencedProvider(["Erreur E17 imprimante", "Vérifiez le bac papier."])
    chat_service = ChatService(db_session, llm_service=LLMService(provider=provider))

    conversation, _ = await chat_service.send_message(chat_user, "Mon imprimante affiche Erreur E17")

    assert conversation.title == "Erreur E17 imprimante"
    # Le titre est demandé à partir du seul message client, avant l'appel de chat.
    assert provider.received_messages_per_call[0][-1] == {
        "role": "user",
        "content": "Mon imprimante affiche Erreur E17",
    }


@pytest.mark.asyncio
async def test_send_message_refines_title_after_second_question(db_session, chat_user):
    # Ordre des appels LLM : titre(Q1) -> réponse(Q1) -> titre affiné(Q1+Q2) -> réponse(Q2).
    provider = SequencedProvider(["Bonjour", "réponse 1", "Erreur E17 imprimante", "réponse 2"])
    chat_service = ChatService(db_session, llm_service=LLMService(provider=provider))

    conversation, _ = await chat_service.send_message(chat_user, "Bonjour")
    assert conversation.title == "Bonjour"

    conversation_again, _ = await chat_service.send_message(
        chat_user, "Mon imprimante affiche Erreur E17", conversation_id=conversation.id
    )

    assert conversation_again.title == "Erreur E17 imprimante"
    # Le titre affiné est demandé à partir des deux questions du client.
    refine_call_messages = provider.received_messages_per_call[2]
    assert refine_call_messages[-1] == {
        "role": "user",
        "content": "Bonjour Mon imprimante affiche Erreur E17",
    }


@pytest.mark.asyncio
async def test_send_message_does_not_touch_title_from_third_question_onward(db_session, chat_user):
    provider = SequencedProvider(
        ["titre 1", "réponse 1", "titre final", "réponse 2", "réponse 3"]
    )
    chat_service = ChatService(db_session, llm_service=LLMService(provider=provider))

    conversation, _ = await chat_service.send_message(chat_user, "premier message")
    conversation, _ = await chat_service.send_message(
        chat_user, "deuxième message", conversation_id=conversation.id
    )
    conversation_final, _ = await chat_service.send_message(
        chat_user, "troisième message", conversation_id=conversation.id
    )

    assert conversation_final.title == "titre final"
    # 2 appels titre (Q1 puis Q1+Q2) + 3 appels chat, aucun appel titre pour Q3.
    assert len(provider.received_messages_per_call) == 5


@pytest.mark.asyncio
async def test_send_message_falls_back_to_truncated_title_when_llm_fails(db_session, chat_user):
    provider = SequencedProvider([LLMRequestError("quota exceeded"), "réponse malgré tout"])
    chat_service = ChatService(db_session, llm_service=LLMService(provider=provider))

    long_message = " ".join(["mot"] * 30)
    conversation, assistant_message = await chat_service.send_message(chat_user, long_message)

    assert conversation.title is not None
    assert conversation.title != long_message
    assert conversation.title.endswith("…")
    assert assistant_message.content == "réponse malgré tout"


__all__: list[str] = []
