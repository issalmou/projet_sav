"""Tests de app.ai.llm.LLMService (tâche 3.4).

Tous les cas sont testés avec un fournisseur factice (aucun appel réseau).
L'appel réel à Gemini est couvert une seule fois pour toute la suite, au
niveau HTTP (tests/test_chat_api.py), pour ne pas épuiser le quota gratuit.
"""
import pytest

from app.ai.exceptions import LLMError, LLMRequestError
from app.ai.llm import LLMService
from app.ai.providers.base import LLMProvider, LLMResult, Message, ToolSpec


class FakeProvider(LLMProvider):
    """Fournisseur factice : rejoue une réponse fixe ou lève une erreur donnée."""

    def __init__(self, reply: str | None = None, error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.received_messages: list[Message] | None = None

    async def agenerate(self, messages: list[Message], **kwargs: object) -> str:
        self.received_messages = messages

        if self.error is not None:
            raise self.error

        return self.reply or ""

    async def agenerate_tools(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResult:
        return LLMResult(text=await self.agenerate(messages))


@pytest.mark.asyncio
async def test_generate_reply_returns_provider_response():
    provider = FakeProvider(reply="Bonjour, comment puis-je vous aider ?")
    service = LLMService(provider=provider)

    reply = await service.generate_reply([{"role": "user", "content": "Bonjour"}])

    assert reply == "Bonjour, comment puis-je vous aider ?"


@pytest.mark.asyncio
async def test_generate_reply_forwards_messages_unchanged():
    provider = FakeProvider(reply="ok")
    service = LLMService(provider=provider)
    messages = [
        {"role": "system", "content": "Tu es un assistant SAV."},
        {"role": "user", "content": "Mon imprimante affiche E17"},
    ]

    await service.generate_reply(messages)

    assert provider.received_messages == messages


@pytest.mark.asyncio
async def test_generate_reply_with_empty_messages_raises_llm_error():
    service = LLMService(provider=FakeProvider(reply="ok"))

    with pytest.raises(LLMError):
        await service.generate_reply([])


@pytest.mark.asyncio
async def test_generate_reply_propagates_provider_error():
    provider = FakeProvider(error=LLMRequestError("quota exceeded"))
    service = LLMService(provider=provider)

    with pytest.raises(LLMRequestError):
        await service.generate_reply([{"role": "user", "content": "Bonjour"}])


@pytest.mark.asyncio
async def test_generate_title_returns_cleaned_provider_response():
    provider = FakeProvider(reply='  "Erreur E17 imprimante."  ')
    service = LLMService(provider=provider)

    title = await service.generate_title("Mon imprimante affiche Erreur E17")

    assert title == "Erreur E17 imprimante"


@pytest.mark.asyncio
async def test_generate_title_sends_title_prompt_and_message_only():
    provider = FakeProvider(reply="Erreur E17 imprimante")
    service = LLMService(provider=provider)

    await service.generate_title("Mon imprimante affiche Erreur E17", preferred_language="en")

    assert provider.received_messages is not None
    assert len(provider.received_messages) == 2
    assert provider.received_messages[0]["role"] == "system"
    assert "anglais" in provider.received_messages[0]["content"]
    assert provider.received_messages[1] == {
        "role": "user",
        "content": "Mon imprimante affiche Erreur E17",
    }


@pytest.mark.asyncio
async def test_generate_title_truncates_long_titles_at_word_boundary():
    provider = FakeProvider(reply="a" * 10 + " " + "b" * 60)
    service = LLMService(provider=provider)

    title = await service.generate_title("message")

    assert title == f"{'a' * 10}…"
    assert len(title) <= 12


@pytest.mark.asyncio
async def test_generate_title_raises_llm_error_when_provider_returns_blank():
    provider = FakeProvider(reply='   ""   ')
    service = LLMService(provider=provider)

    with pytest.raises(LLMRequestError):
        await service.generate_title("message")


@pytest.mark.asyncio
async def test_generate_title_propagates_provider_error():
    provider = FakeProvider(error=LLMRequestError("quota exceeded"))
    service = LLMService(provider=provider)

    with pytest.raises(LLMRequestError):
        await service.generate_title("message")


__all__: list[str] = []
