"""Tests de DiagnosticService (CDC semaine 5 : diagnostic automatique)."""
import logging
import uuid

import pytest
import pytest_asyncio

from sqlalchemy import delete

from app.ai.exceptions import EmbeddingError, LLMRequestError
from app.ai.llm import LLMService
from app.ai.providers.base import LLMProvider, Message as LLMMessage
from app.ai.rag.retriever import RetrievedChunk
from app.models.product import Product
from app.models.ticket import Ticket
from app.schemas.product import ProductCreate
from app.schemas.user import UserCreate
from app.services.diagnostic_service import (
    TICKET_DESCRIPTION_MAX_LENGTH,
    DiagnosticService,
    _FALLBACK_TICKET_DESCRIPTION_PREFIX,
    _TICKET_CREATION_FAILURE_MESSAGE,
)
from app.services.product_service import ProductService
from app.services.ticket_service import TicketService
from app.services.user_service import UserService
from app.utils.constants import DiagnosticStatus
from conftest import NullRetriever, StubRetriever


class FakeProvider(LLMProvider):
    """Fournisseur factice : rejoue une réponse fixe, sans appel réseau."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.received_messages: list[LLMMessage] | None = None

    async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
        self.received_messages = messages
        return self.reply


class _RaisingRetriever:
    """Double de RetrieverService qui lève systématiquement l'exception fournie."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def retrieve(self, question: str, *, product_id=None) -> list:
        raise self._exc


class SequencedProvider(LLMProvider):
    """Fournisseur factice qui rejoue une réponse différente à chaque appel."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.received_messages_per_call: list[list[LLMMessage]] = []
        self._calls = 0

    async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
        self._calls += 1
        self.received_messages_per_call.append(messages)
        if not self.replies:
            raise AssertionError(
                f"SequencedProvider exhausted after {self._calls - 1} scripted replies : "
                "un appel LLM supplémentaire n'a pas été prévu par ce test."
            )
        return self.replies.pop(0)


@pytest_asyncio.fixture
async def diag_user(db_session):
    service = UserService(db_session)
    email = f"diag.{uuid.uuid4().hex[:10]}@example.com"
    user = await service.create_user(UserCreate(email=email, password="ValidPass1"))
    user_id = user.id  # capturé avant le test : un rollback() y expirerait `user`

    yield user

    # client_id est en RESTRICT (tâche 3) : supprimer les tickets créés par
    # le diagnostic (tâche 7) avant de pouvoir supprimer l'utilisateur.
    await db_session.execute(delete(Ticket).where(Ticket.client_id == user_id))
    await db_session.commit()

    still_there = await service.get_user_by_id(user_id)
    if still_there is not None:
        await db_session.delete(still_there)
        await db_session.commit()


def _diagnostic_service(db_session, reply: str) -> DiagnosticService:
    return DiagnosticService(
        db_session, llm_service=LLMService(provider=FakeProvider(reply)), retriever=NullRetriever()
    )


@pytest.mark.asyncio
async def test_diagnose_parses_resolved_status_and_strips_marker(db_session, diag_user):
    service = _diagnostic_service(
        db_session, "Vérifiez que le bac papier est bien inséré.\n[STATUT: RESOLU]"
    )

    result = await service.diagnose(diag_user, "Mon imprimante affiche Erreur E17")

    assert result.status is DiagnosticStatus.RESOLVED
    assert result.message.content == "Vérifiez que le bac papier est bien inséré."
    assert "[STATUT" not in result.message.content


@pytest.mark.asyncio
async def test_diagnose_parses_in_progress_status(db_session, diag_user):
    service = _diagnostic_service(
        db_session, "Le problème persiste-t-il après ce redémarrage ?\n[STATUT: EN_COURS]"
    )

    result = await service.diagnose(diag_user, "Mon imprimante affiche Erreur E17")

    assert result.status is DiagnosticStatus.IN_PROGRESS
    assert result.message.content == "Le problème persiste-t-il après ce redémarrage ?"


@pytest.mark.asyncio
async def test_diagnose_downgrades_escalate_to_in_progress_on_first_message(db_session, diag_user):
    service = _diagnostic_service(
        db_session, "Je ne parviens pas à résoudre ce problème.\n[STATUT: A_ESCALADER]"
    )

    result = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")

    assert result.status is DiagnosticStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_diagnose_allows_escalate_from_second_message_onward(db_session, diag_user):
    # Ordre des appels LLM (ChatService génère aussi le titre) :
    # titre(Q1) -> diagnostic(Q1) -> titre affiné(Q1+Q2) -> diagnostic(Q2).
    provider = SequencedProvider(
        [
            "Four qui ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème.\n[STATUT: A_ESCALADER]",
        ]
    )
    service = DiagnosticService(
        db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever()
    )

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")
    assert first.status is DiagnosticStatus.IN_PROGRESS

    second = await service.diagnose(
        diag_user, "Oui, le fusible est bon, toujours rien", conversation_id=first.conversation.id
    )

    assert second.status is DiagnosticStatus.ESCALATE
    assert second.message.content == "Je ne parviens pas à résoudre ce problème."


@pytest.mark.asyncio
async def test_diagnose_defaults_to_in_progress_when_marker_missing(db_session, diag_user):
    service = _diagnostic_service(db_session, "Réponse sans marqueur de statut.")

    result = await service.diagnose(diag_user, "Bonjour")

    assert result.status is DiagnosticStatus.IN_PROGRESS
    assert result.message.content == "Réponse sans marqueur de statut."


@pytest.mark.asyncio
async def test_diagnose_persists_cleaned_content(db_session, diag_user):
    service = _diagnostic_service(db_session, "Contenu final.\n[STATUT: RESOLU]")

    result = await service.diagnose(diag_user, "Bonjour")

    reloaded_history = await service._chat_service.get_history(result.conversation.id, diag_user.id)
    assistant_messages = [message for message in reloaded_history if message.role == "assistant"]

    assert assistant_messages[0].content == "Contenu final."


@pytest.mark.asyncio
async def test_diagnose_includes_status_instruction_in_system_prompt(db_session, diag_user):
    provider = FakeProvider("ok\n[STATUT: RESOLU]")
    service = DiagnosticService(
        db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever()
    )

    await service.diagnose(diag_user, "Bonjour")

    assert provider.received_messages is not None
    system_message = provider.received_messages[0]
    assert system_message["role"] == "system"
    assert "[STATUT: RESOLU]" in system_message["content"]


# --- Intégration ticket sur escalade (tâche 7) -----------------------------


@pytest.mark.asyncio
async def test_diagnose_does_not_create_ticket_when_not_escalating(db_session, diag_user):
    service = _diagnostic_service(db_session, "Vérifiez le bac papier.\n[STATUT: EN_COURS]")

    result = await service.diagnose(diag_user, "Mon imprimante affiche Erreur E17")

    assert result.status is DiagnosticStatus.IN_PROGRESS
    assert result.ticket is None


@pytest.mark.asyncio
async def test_diagnose_proposes_ticket_without_creating_it_on_first_escalate(db_session, diag_user):
    """Sur A_ESCALADER, aucun ticket n'est créé immédiatement : le client est seulement informé."""

    # titre(Q1) -> diagnostic(Q1, EN_COURS) -> titre affiné(Q1+Q2) -> diagnostic(Q2, A_ESCALADER)
    provider = SequencedProvider(
        [
            "Four ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
        ]
    )
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")
    second = await service.diagnose(
        diag_user, "Oui, le fusible est bon, toujours rien", conversation_id=first.conversation.id
    )

    assert second.status is DiagnosticStatus.ESCALATE
    assert second.ticket is None
    assert second.conversation.pending_ticket_confirmation is True


@pytest.mark.asyncio
async def test_diagnose_creates_ticket_after_explicit_confirmation(db_session, diag_user):
    # titre(Q1) -> diag(Q1, EN_COURS) -> titre affiné(Q1+Q2) -> diag(Q2, A_ESCALADER)
    # -> confirmation(Q3, OUI, pas de titre) -> synthèse de la description du ticket
    provider = SequencedProvider(
        [
            "Four ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
            "Très bien, votre ticket va être créé.\n[CONFIRMATION: OUI]",
            "Le four ne s'allume plus malgré la vérification du fusible thermique ; "
            "nécessite une intervention technique.\n[PRODUIT: AUCUN]",
        ]
    )
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")
    second = await service.diagnose(
        diag_user, "Oui, le fusible est bon, toujours rien", conversation_id=first.conversation.id
    )
    third = await service.diagnose(
        diag_user, "Oui, créez le ticket", conversation_id=first.conversation.id
    )

    assert second.ticket is None  # rien n'a été créé au moment de la proposition
    assert third.status is DiagnosticStatus.ESCALATE
    assert third.ticket is not None
    assert third.ticket.client_id == diag_user.id
    assert third.ticket.conversation_id == third.conversation.id
    assert third.ticket.status == "open"
    assert third.ticket.title == third.conversation.title
    # Description générée par l'appel de synthèse dédié, pas la concaténation brute :
    assert third.ticket.description == (
        "Le four ne s'allume plus malgré la vérification du fusible thermique ; "
        "nécessite une intervention technique."
    )
    assert "Oui, créez le ticket" not in third.ticket.description  # jamais la confirmation elle-même
    assert third.ticket.product_id is None  # [PRODUIT: AUCUN] -> jamais d'ID deviné
    assert third.conversation.pending_ticket_confirmation is False


@pytest.mark.asyncio
async def test_diagnose_creates_no_ticket_when_client_declines(db_session, diag_user):
    provider = SequencedProvider(
        [
            "Four ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
            "Entendu, n'hésitez pas à revenir si besoin.\n[CONFIRMATION: NON]",
        ]
    )
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")
    second = await service.diagnose(
        diag_user, "Oui, le fusible est bon, toujours rien", conversation_id=first.conversation.id
    )
    third = await service.diagnose(
        diag_user, "Non merci, je vais réessayer seul", conversation_id=first.conversation.id
    )

    assert second.ticket is None
    assert third.ticket is None
    assert third.status is DiagnosticStatus.IN_PROGRESS
    assert third.conversation.pending_ticket_confirmation is False


@pytest.mark.asyncio
async def test_diagnose_keeps_awaiting_confirmation_when_answer_is_unclear(db_session, diag_user):
    provider = SequencedProvider(
        [
            "Four ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
            "Je ne suis pas sûr de comprendre, souhaitez-vous un ticket ?\n[CONFIRMATION: INCERTAIN]",
        ]
    )
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")
    second = await service.diagnose(
        diag_user, "Oui, le fusible est bon, toujours rien", conversation_id=first.conversation.id
    )
    third = await service.diagnose(
        diag_user, "Peut-être, je ne sais pas trop", conversation_id=first.conversation.id
    )

    assert third.ticket is None
    assert third.status is DiagnosticStatus.ESCALATE
    assert third.conversation.pending_ticket_confirmation is True


@pytest.mark.asyncio
async def test_diagnose_confirmation_defaults_to_unclear_when_marker_missing(db_session, diag_user):
    """Repli de sécurité : marqueur de confirmation absent/mal formé -> jamais de création de ticket."""

    provider = SequencedProvider(
        [
            "Four ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
            "Réponse sans marqueur de confirmation.",
        ]
    )
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")
    second = await service.diagnose(
        diag_user, "Oui, le fusible est bon, toujours rien", conversation_id=first.conversation.id
    )
    third = await service.diagnose(
        diag_user, "Une réponse quelconque", conversation_id=first.conversation.id
    )

    assert third.ticket is None
    assert third.conversation.pending_ticket_confirmation is True


@pytest.mark.asyncio
async def test_diagnose_reuses_active_ticket_without_reproposing(db_session, diag_user):
    """Un ticket actif existant n'est jamais dupliqué : pas de nouvelle proposition tant qu'il reste ouvert."""

    provider = SequencedProvider(
        [
            "Four ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
            "Très bien, votre ticket va être créé.\n[CONFIRMATION: OUI]",
            "Le four ne s'allume plus malgré la vérification du fusible.\n[PRODUIT: AUCUN]",  # synthèse
            "Toujours pas de solution, le ticket est déjà en cours.\n[STATUT: A_ESCALADER]",
        ]
    )
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")
    second = await service.diagnose(
        diag_user, "Oui, le fusible est bon, toujours rien", conversation_id=first.conversation.id
    )
    third = await service.diagnose(
        diag_user, "Oui, créez le ticket", conversation_id=first.conversation.id
    )
    fourth = await service.diagnose(
        diag_user, "J'ai aussi vérifié la prise", conversation_id=first.conversation.id
    )

    assert third.ticket is not None
    assert fourth.ticket is not None
    assert fourth.ticket.id == third.ticket.id  # même ticket réutilisé, pas de doublon (pas de resynthèse)
    assert fourth.conversation.pending_ticket_confirmation is False  # pas de nouvelle proposition


@pytest.mark.asyncio
async def test_diagnose_creates_new_ticket_when_previous_is_closed(db_session, diag_user):
    provider = SequencedProvider(
        [
            "Four ne s'allume plus",
            "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
            "Panne four ne s'allume plus",
            "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
            "Très bien, votre ticket va être créé.\n[CONFIRMATION: OUI]",
            "Le four ne s'allume plus malgré la vérification du fusible.\n[PRODUIT: AUCUN]",  # synthèse #1
            "Toujours rien après réparation, voulez-vous un nouveau ticket ?\n[STATUT: A_ESCALADER]",
            "Entendu, un nouveau ticket va être créé.\n[CONFIRMATION: OUI]",
            "Panne toujours présente après une première réparation infructueuse.\n[PRODUIT: AUCUN]",  # synthèse #2
        ]
    )
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")
    second = await service.diagnose(
        diag_user, "Oui, le fusible est bon, toujours rien", conversation_id=first.conversation.id
    )
    third = await service.diagnose(
        diag_user, "Oui, créez le ticket", conversation_id=first.conversation.id
    )
    assert third.ticket is not None

    # Un membre du staff clôture le ticket (mutation directe, pas de RBAC à tester ici).
    third.ticket.status = "closed"
    db_session.add(third.ticket)
    await db_session.commit()

    fourth = await service.diagnose(
        diag_user, "Ça recommence après une nouvelle tentative", conversation_id=first.conversation.id
    )
    assert fourth.ticket is None  # nouvelle proposition, pas de création immédiate
    assert fourth.conversation.pending_ticket_confirmation is True

    fifth = await service.diagnose(
        diag_user, "Oui, créez-en un nouveau", conversation_id=first.conversation.id
    )
    assert fifth.ticket is not None
    assert fifth.ticket.id != third.ticket.id  # nouveau ticket, l'ancien est closed


# --- Description synthétisée par LLM + identification produit via RAG -----


async def _diagnose_to_confirmed_ticket(service: DiagnosticService, diag_user, product_id=None):
    """Enchaîne les 3 tours nécessaires (proposition -> confirmation) et retourne le résultat final."""

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout", product_id=product_id)
    await service.diagnose(
        diag_user,
        "Oui, le fusible est bon, toujours rien",
        conversation_id=first.conversation.id,
        product_id=product_id,
    )
    return await service.diagnose(
        diag_user, "Oui, créez le ticket", conversation_id=first.conversation.id, product_id=product_id
    )


_ESCALATION_REPLIES = [
    "Four ne s'allume plus",
    "Avez-vous vérifié le fusible ?\n[STATUT: EN_COURS]",
    "Panne four ne s'allume plus",
    "Je ne parviens pas à résoudre ce problème. Voulez-vous un ticket ?\n[STATUT: A_ESCALADER]",
    "Très bien, votre ticket va être créé.\n[CONFIRMATION: OUI]",
]


def _corroborating_retriever(product: Product) -> StubRetriever:
    """StubRetriever dont le chunk mentionne explicitement le produit, pour satisfaire la
    vérification croisée (`DiagnosticService._resolve_product_id`)."""

    return StubRetriever(
        [
            RetrievedChunk(
                text=f"Guide de dépannage pour {product.name} (référence {product.reference}).",
                document_id=uuid.uuid4(),
                title=f"Manuel {product.name}",
                category="manuals",
                distance=0.1,
            )
        ]
    )


@pytest.mark.asyncio
async def test_diagnose_resolves_product_by_exact_reference(db_session, diag_user, product):
    provider = SequencedProvider(
        [*_ESCALATION_REPLIES, f"Panne confirmée sur l'appareil référencé.\n[PRODUIT: {product.reference}]"]
    )
    service = DiagnosticService(
        db_session, llm_service=LLMService(provider=provider), retriever=_corroborating_retriever(product)
    )

    result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id == product.id


@pytest.mark.asyncio
async def test_diagnose_resolves_product_by_exact_name_case_insensitive(db_session, diag_user, product):
    identifier = product.name.upper()  # correspondance insensible à la casse (règle validée)
    provider = SequencedProvider(
        [*_ESCALATION_REPLIES, f"Panne confirmée sur l'appareil identifié.\n[PRODUIT: {identifier}]"]
    )
    service = DiagnosticService(
        db_session, llm_service=LLMService(provider=provider), retriever=_corroborating_retriever(product)
    )

    result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id == product.id


@pytest.mark.asyncio
async def test_diagnose_leaves_product_none_when_not_corroborated_by_rag_context(db_session, diag_user, product):
    """Le produit existe bien en base (correspondance exacte), mais n'apparaît dans aucun chunk RAG
    retrouvé pour cette synthèse : la résolution doit rester prudente (règle validée)."""

    provider = SequencedProvider([*_ESCALATION_REPLIES, f"Panne confirmée.\n[PRODUIT: {product.reference}]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id is None  # correspondance DB exacte mais non corroborée par le RAG


@pytest.mark.asyncio
async def test_diagnose_keeps_known_product_id_ignoring_llm_suggestion(db_session, diag_user, product):
    """Un product_id déjà connu en amont a priorité : la suggestion du LLM n'est jamais consultée."""

    unrelated_reference = f"REF-{uuid.uuid4().hex[:8]}"  # ne correspond à aucun produit réel
    provider = SequencedProvider([*_ESCALATION_REPLIES, f"Panne confirmée.\n[PRODUIT: {unrelated_reference}]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    result = await _diagnose_to_confirmed_ticket(service, diag_user, product_id=product.id)

    assert result.ticket is not None
    assert result.ticket.product_id == product.id


@pytest.mark.asyncio
async def test_diagnose_truncates_overly_long_description(db_session, diag_user):
    """Filet de sécurité technique : une description trop longue est plafonnée, au dernier mot entier."""

    overly_long_text = "Symptôme détaillé du client. " * 60  # bien au-delà de TICKET_DESCRIPTION_MAX_LENGTH
    provider = SequencedProvider([*_ESCALATION_REPLIES, f"{overly_long_text}\n[PRODUIT: AUCUN]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert len(result.ticket.description) <= TICKET_DESCRIPTION_MAX_LENGTH + 1  # +1 pour l'ellipse finale
    assert result.ticket.description.endswith("…")


@pytest.mark.asyncio
async def test_diagnose_leaves_product_none_when_identifier_matches_nothing(db_session, diag_user):
    provider = SequencedProvider(
        [*_ESCALATION_REPLIES, "Panne sur un four non référencé dans le catalogue.\n[PRODUIT: FourInconnuXYZ]"]
    )
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id is None  # aucune correspondance -> jamais d'ID deviné


@pytest.mark.asyncio
async def test_diagnose_leaves_product_none_when_name_is_ambiguous(db_session, diag_user, product):
    """Deux produits partageant le même nom : la correspondance par nom devient ambiguë, jamais tranchée."""

    duplicate = Product(reference=f"REF-{uuid.uuid4().hex[:8]}", name=product.name)
    db_session.add(duplicate)
    await db_session.commit()

    provider = SequencedProvider([*_ESCALATION_REPLIES, f"Panne confirmée.\n[PRODUIT: {product.name}]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id is None

    await db_session.delete(duplicate)
    await db_session.commit()


@pytest.mark.asyncio
async def test_diagnose_creates_ticket_with_plain_description_when_synthesis_fails(db_session, diag_user, caplog):
    """La synthèse LLM/RAG est optionnelle : son échec ne doit jamais empêcher la création du ticket."""

    class FailingSynthesisProvider(LLMProvider):
        """Répond normalement au diagnostic et à la confirmation, échoue uniquement pour la synthèse."""

        def __init__(self, replies: list[str]) -> None:
            self.replies = list(replies)

        async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
            if not self.replies:
                raise LLMRequestError("Fournisseur indisponible pour la synthèse du ticket")
            return self.replies.pop(0)

    provider = FailingSynthesisProvider(list(_ESCALATION_REPLIES))
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    with caplog.at_level(logging.WARNING):
        result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None  # la synthèse échoue, le ticket est quand même créé
    assert result.ticket.product_id is None
    assert _FALLBACK_TICKET_DESCRIPTION_PREFIX in result.ticket.description  # phrase statique standard
    assert "Oui, le fusible est bon, toujours rien" in result.ticket.description  # + échange réel conservé
    assert any(record.levelname == "WARNING" for record in caplog.records)  # échec externe attendu -> WARNING


# --- Vérification croisée produit : casse, séparateurs, références courtes ------


@pytest.mark.asyncio
async def test_diagnose_resolves_product_with_different_case_in_context(db_session, diag_user, product):
    chunk = RetrievedChunk(
        text=f"Guide pour {product.reference.lower()}.",
        document_id=uuid.uuid4(),
        title="Manuel produit",
        category="manuals",
        distance=0.1,
    )
    provider = SequencedProvider([*_ESCALATION_REPLIES, f"Panne confirmée.\n[PRODUIT: {product.reference}]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=StubRetriever([chunk]))

    result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id == product.id


@pytest.mark.asyncio
async def test_diagnose_resolves_product_with_different_separators_in_context(db_session, diag_user, product):
    """Référence écrite avec des espaces à la place des tirets (ex. "IMP X100" ~ "IMP-X100")."""

    reference_with_spaces = product.reference.replace("-", " ")
    chunk = RetrievedChunk(
        text=f"Guide pour la référence {reference_with_spaces}.",
        document_id=uuid.uuid4(),
        title="Manuel produit",
        category="manuals",
        distance=0.1,
    )
    provider = SequencedProvider([*_ESCALATION_REPLIES, f"Panne confirmée.\n[PRODUIT: {product.reference}]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=StubRetriever([chunk]))

    result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id == product.id


@pytest.mark.asyncio
async def test_diagnose_rejects_short_generic_reference_as_uncorroborated(db_session, diag_user):
    """Une référence courte/générique ("F1") ne doit jamais être corroborée automatiquement,
    même si elle apparaît comme sous-chaîne d'un texte plus long ("F100")."""

    product_service = ProductService(db_session)
    short_product = await product_service.create_product(ProductCreate(reference="F1", name="Four compact F1"))

    chunk = RetrievedChunk(
        text="Ce four F100 nécessite une vérification du fusible thermique.",
        document_id=uuid.uuid4(),
        title="Manuel four",
        category="manuals",
        distance=0.1,
    )
    provider = SequencedProvider([*_ESCALATION_REPLIES, "Panne confirmée.\n[PRODUIT: F1]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=StubRetriever([chunk]))

    result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id is None  # référence trop courte, jamais corroborée automatiquement

    await product_service.delete_product(short_product.id)


@pytest.mark.asyncio
async def test_diagnose_rejects_product_suggested_by_llm_not_mentioned_in_context(db_session, diag_user, product):
    """Le LLM propose la référence d'un VRAI produit du catalogue, mais le contexte RAG
    retrouvé ne le mentionne pas du tout : reste non corroboré malgré la correspondance DB exacte."""

    unrelated_chunk = RetrievedChunk(
        text="Contenu générique sans rapport avec ce produit.",
        document_id=uuid.uuid4(),
        title="Document générique",
        category="faq",
        distance=0.2,
    )
    provider = SequencedProvider([*_ESCALATION_REPLIES, f"Panne confirmée.\n[PRODUIT: {product.reference}]"])
    service = DiagnosticService(
        db_session, llm_service=LLMService(provider=provider), retriever=StubRetriever([unrelated_chunk])
    )

    result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id is None


# --- Observabilité : RAG / LLM / résolution produit distingués -----------------


@pytest.mark.asyncio
async def test_diagnose_continues_synthesis_without_context_when_rag_fails(db_session, diag_user, caplog):
    """Un échec RAG attendu (EmbeddingError) ne bloque pas la synthèse : elle continue sans contexte."""

    provider = SequencedProvider([*_ESCALATION_REPLIES, "Synthèse malgré RAG indisponible.\n[PRODUIT: AUCUN]"])
    service = DiagnosticService(
        db_session,
        llm_service=LLMService(provider=provider),
        retriever=_RaisingRetriever(EmbeddingError("Fournisseur d'embeddings indisponible")),
    )

    with caplog.at_level(logging.WARNING):
        result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.description == "Synthèse malgré RAG indisponible."
    assert any(
        record.levelname == "WARNING" and "RAG" in record.message for record in caplog.records
    )


@pytest.mark.asyncio
async def test_diagnose_logs_error_when_rag_fails_unexpectedly(db_session, diag_user, caplog):
    provider = SequencedProvider(
        [*_ESCALATION_REPLIES, "Synthèse malgré erreur RAG inattendue.\n[PRODUIT: AUCUN]"]
    )
    service = DiagnosticService(
        db_session,
        llm_service=LLMService(provider=provider),
        retriever=_RaisingRetriever(RuntimeError("Bug inattendu dans le retriever")),
    )

    with caplog.at_level(logging.ERROR):
        result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.description == "Synthèse malgré erreur RAG inattendue."
    assert any(
        record.levelname == "ERROR" and "RAG" in record.message for record in caplog.records
    )


@pytest.mark.asyncio
async def test_diagnose_logs_error_when_llm_synthesis_fails_unexpectedly(db_session, diag_user, caplog):
    """Une exception inattendue (pas LLMError) pendant l'appel LLM -> niveau ERROR, ticket quand même créé."""

    class BuggyProvider(LLMProvider):
        def __init__(self, replies: list[str]) -> None:
            self.replies = list(replies)

        async def agenerate(self, messages: list[LLMMessage], **kwargs: object) -> str:
            if not self.replies:
                raise RuntimeError("Bug inattendu dans le provider")
            return self.replies.pop(0)

    provider = BuggyProvider(list(_ESCALATION_REPLIES))
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    with caplog.at_level(logging.ERROR):
        result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id is None
    assert "Oui, le fusible est bon, toujours rien" in result.ticket.description
    assert any(record.levelname == "ERROR" for record in caplog.records)


@pytest.mark.asyncio
async def test_diagnose_keeps_llm_description_when_product_resolution_fails_unexpectedly(
    db_session, diag_user, product, monkeypatch, caplog
):
    """Une erreur inattendue pendant la résolution DB du produit (après une synthèse LLM
    réussie) conserve la description générée, product_id revient à None."""

    async def _boom(self, reference):
        raise RuntimeError("Base de données indisponible")

    monkeypatch.setattr(ProductService, "get_product_by_reference", _boom)

    provider = SequencedProvider(
        [*_ESCALATION_REPLIES, f"Panne confirmée sur l'appareil référencé.\n[PRODUIT: {product.reference}]"]
    )
    service = DiagnosticService(
        db_session, llm_service=LLMService(provider=provider), retriever=_corroborating_retriever(product)
    )

    with caplog.at_level(logging.ERROR):
        result = await _diagnose_to_confirmed_ticket(service, diag_user)

    assert result.ticket is not None
    assert result.ticket.product_id is None
    assert result.ticket.description == "Panne confirmée sur l'appareil référencé."  # description LLM conservée
    assert any(record.levelname == "ERROR" for record in caplog.records)


# --- Langue de la description (user.preferred_language) ------------------------


@pytest.mark.asyncio
async def test_diagnose_synthesis_prompt_uses_client_preferred_language_english(db_session, diag_user):
    diag_user.preferred_language = "en"

    provider = SequencedProvider([*_ESCALATION_REPLIES, "Confirmed issue.\n[PRODUIT: AUCUN]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    await _diagnose_to_confirmed_ticket(service, diag_user)

    synthesis_system_message = provider.received_messages_per_call[-1][0]
    assert synthesis_system_message["role"] == "system"
    assert "anglais" in synthesis_system_message["content"]


@pytest.mark.asyncio
async def test_diagnose_synthesis_prompt_uses_client_preferred_language_arabic(db_session, diag_user):
    diag_user.preferred_language = "ar"

    provider = SequencedProvider([*_ESCALATION_REPLIES, "مشكلة مؤكدة.\n[PRODUIT: AUCUN]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    await _diagnose_to_confirmed_ticket(service, diag_user)

    synthesis_system_message = provider.received_messages_per_call[-1][0]
    assert "arabe" in synthesis_system_message["content"]


@pytest.mark.asyncio
async def test_diagnose_synthesis_prompt_falls_back_to_french_for_unsupported_language(db_session, diag_user):
    diag_user.preferred_language = "de"  # non supporté par la plateforme

    provider = SequencedProvider([*_ESCALATION_REPLIES, "Panne bestätigt.\n[PRODUIT: AUCUN]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    await _diagnose_to_confirmed_ticket(service, diag_user)

    synthesis_system_message = provider.received_messages_per_call[-1][0]
    assert "français" in synthesis_system_message["content"]


# --- Échec inattendu de la création du ticket après confirmation ---------------


@pytest.mark.asyncio
async def test_diagnose_asks_to_reconfirm_when_ticket_creation_fails_unexpectedly(
    db_session, diag_user, monkeypatch, caplog
):
    """La création du ticket échoue après un OUI -> jamais annoncé comme créé, workflow réouvrable."""

    calls = {"count": 0}
    original_create_ticket = TicketService.create_ticket

    async def _flaky_create_ticket(self, user, data, *, conversation_id=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("Base de données indisponible")
        return await original_create_ticket(self, user, data, conversation_id=conversation_id)

    monkeypatch.setattr(TicketService, "create_ticket", _flaky_create_ticket)

    provider = SequencedProvider([*_ESCALATION_REPLIES, "Nouvelle tentative confirmée.\n[CONFIRMATION: OUI]"])
    service = DiagnosticService(db_session, llm_service=LLMService(provider=provider), retriever=NullRetriever())

    first = await service.diagnose(diag_user, "Mon four ne s'allume plus du tout")
    await service.diagnose(
        diag_user, "Oui, le fusible est bon, toujours rien", conversation_id=first.conversation.id
    )

    with caplog.at_level(logging.ERROR):
        third = await service.diagnose(
            diag_user, "Oui, créez le ticket", conversation_id=first.conversation.id
        )

    assert third.ticket is None
    assert third.message.content == _TICKET_CREATION_FAILURE_MESSAGE  # jamais "créé" affirmé à tort
    assert third.conversation.pending_ticket_confirmation is True  # workflow toujours ouvert
    assert any(record.levelname == "ERROR" for record in caplog.records)

    # Note : la reconfirmation réussie (nouvelle requête HTTP -> nouvelle session
    # DB via get_db()) n'est pas simulée ici sur la même session partagée par ce
    # test : un rollback suivi d'une réutilisation de session pour de nouvelles
    # requêtes est un scénario propre aux fixtures de test (session unique et
    # longue durée), pas au fonctionnement réel en production.


__all__: list[str] = []
