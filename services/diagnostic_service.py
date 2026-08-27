"""Service de diagnostic automatique (CDC semaine 5).

Réutilise ChatService (conversation, historique, RAG, LLM) sans dupliquer sa
logique : ce service ajoute uniquement l'instruction de statut de diagnostic
au prompt système via `extra_system_instructions`, puis interprète le statut
que le LLM a renvoyé. Sur escalade (statut A_ESCALADER), le ticket n'est PAS
créé immédiatement : le client est informé et une confirmation explicite lui
est demandée (`Conversation.pending_ticket_confirmation`). Ce n'est qu'après
un "oui" clair, sur un tour de conversation ultérieur, que la création est
déléguée à TicketService, sans dupliquer sa logique d'accès ni de
dédoublonnage (`get_active_ticket_by_conversation`).

À la création réelle du ticket, une description technique et une tentative
d'identification du produit sont générées par un appel LLM dédié, réutilisant
le RAG existant (`RetrieverService.retrieve`, aucune nouvelle heuristique de
détection produit) et `ProductService` (correspondance exacte uniquement,
jamais d'ID deviné). Cet enrichissement est optionnel : toute erreur retombe
sur une description simple, sans jamais empêcher la création du ticket.
"""
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.exceptions import EmbeddingError, LLMError
from app.ai.llm import LLMService
from app.ai.prompts import (
    DIAGNOSTIC_STATUS_INSTRUCTION,
    DIAGNOSTIC_STATUS_MARKERS,
    TICKET_CONFIRMATION_INSTRUCTION,
    TICKET_CONFIRMATION_MARKERS,
    build_context_section,
    build_ticket_synthesis_instruction,
)
from app.ai.rag.retriever import RetrievedChunk, RetrieverService
from app.core.logger import logger
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketAutoCreate
from app.services.chat_service import ChatService
from app.services.product_service import ProductService
from app.services.ticket_service import TicketService
from app.utils.constants import DiagnosticStatus, TicketConfirmation

# Reconnaît la dernière ligne au format "[STATUT: <MARQUEUR>]", avec ou sans
# saut de ligne/espaces finaux (le LLM ajoute parfois un espace superflu).
_STATUS_MARKER_PATTERN = re.compile(
    r"\n?\[STATUT:\s*(" + "|".join(DIAGNOSTIC_STATUS_MARKERS) + r")\]\s*$"
)

# Même principe que _STATUS_MARKER_PATTERN, pour le marqueur de confirmation
# explicite du client (oui/non/incertain) attendu lorsqu'un ticket a déjà été
# proposé (cf. TICKET_CONFIRMATION_INSTRUCTION).
_CONFIRMATION_MARKER_PATTERN = re.compile(
    r"\n?\[CONFIRMATION:\s*(" + "|".join(TICKET_CONFIRMATION_MARKERS) + r")\]\s*$"
)

# Reconnaît la dernière ligne au format "[PRODUIT: <identifiant libre>]", à la
# différence de _STATUS_MARKER_PATTERN/_CONFIRMATION_MARKER_PATTERN : le
# contenu n'est pas restreint à un petit vocabulaire fixe (référence ou nom de
# produit en texte libre, ou "AUCUN").
_PRODUCT_MARKER_PATTERN = re.compile(r"\n?\[PRODUIT:\s*(.+?)\]\s*$", re.DOTALL)

_FALLBACK_TICKET_TITLE = "Ticket créé automatiquement par le diagnostic"

# Message renvoyé au client si la création du ticket échoue de façon inattendue APRÈS
# une confirmation "oui" (pas un enrichissement optionnel cette fois : l'action elle-même).
# Jamais de détail technique ; invite explicitement à reconfirmer pour relancer le workflow
# (pending_ticket_confirmation reste vrai en base, cf. _handle_confirmation_turn).
_TICKET_CREATION_FAILURE_MESSAGE = (
    "Une erreur technique est survenue lors de la création de votre ticket. "
    "Merci de confirmer à nouveau (répondez « oui ») pour réessayer."
)

# Phrase statique standard utilisée quand la synthèse LLM échoue : jamais une
# trace d'exception, toujours une formulation professionnelle stable.
_FALLBACK_TICKET_DESCRIPTION_PREFIX = (
    "Le problème signalé par le client n'a pas pu être résolu lors du diagnostic automatique. "
    "Une intervention technique est nécessaire."
)

# Filet de sécurité technique en complément de la consigne de longueur du
# prompt (`build_ticket_synthesis_instruction`) : une instruction textuelle
# n'est jamais garantie à 100 % d'être respectée par le LLM. Marge au-delà des
# ~600 caractères demandés dans le prompt pour ne tronquer que les vrais excès.
TICKET_DESCRIPTION_MAX_LENGTH = 800

# Sous ce nombre de caractères normalisés, une référence/un nom est considéré
# trop court/générique pour être corroboré de façon fiable (règle validée) :
# product_id reste None plutôt que de risquer une correspondance accidentelle.
MIN_REFERENCE_LENGTH_FOR_MATCH = 4
MIN_NAME_LENGTH_FOR_MATCH = 4

# Nombre maximal de mots consécutifs combinés lors de la normalisation d'une
# référence produit : permet de reconnaître "IMP X100" comme équivalent à
# "IMP-X100" (espace à la place d'un tiret) sans jamais fusionner des mots non
# adjacents ni tout le texte du document (ce qui réintroduirait un risque de
# coïncidence sur une référence courte).
_MAX_WORDS_FOR_REFERENCE_MATCH = 3

_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class DiagnosticResult:
    """Résultat d'un tour de diagnostic : réponse de l'agent + statut de résolution.

    `ticket` n'est renseigné que si `status is DiagnosticStatus.ESCALATE`
    (ticket réutilisé ou nouvellement créé, tâche 7) ; `None` sinon.
    """

    conversation: Conversation
    message: Message
    status: DiagnosticStatus
    ticket: Ticket | None = None


class DiagnosticService:
    """Orchestrateur du diagnostic automatique : Chat + RAG + LLM, statut de résolution en plus."""

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService | None = None,
        retriever: RetrieverService | None = None,
    ) -> None:
        self.session = session
        # Conservés ici (pas seulement transmis à ChatService) : la synthèse de
        # ticket (_synthesize_ticket_description_and_product) a besoin d'appeler
        # le même LLM et le même RAG directement, sans passer par ChatService.
        self._llm_service = llm_service or LLMService()
        self._retriever = retriever or RetrieverService()
        self._chat_service = ChatService(session, llm_service=self._llm_service, retriever=self._retriever)
        self._ticket_service = TicketService(session)

    async def diagnose(
        self,
        user: User,
        content: str,
        conversation_id: UUID | None = None,
        product_id: UUID | None = None,
    ) -> DiagnosticResult:
        """Traite un message dans le cadre d'un diagnostic et retourne le statut associé.

        Règle CDC §14 (exemple E17) : le diagnostic est conversationnel, l'IA
        vérifie avant de conclure. On n'escalade donc jamais dès le tout
        premier message d'une conversation, même si le LLM le demande.

        Sur escalade (A_ESCALADER), aucun ticket n'est créé immédiatement :
        le client est informé et invité à confirmer. Si cette conversation a
        déjà une proposition en attente (`Conversation.pending_ticket_confirmation`)
        et qu'aucun ticket actif n'existe encore, ce tour est traité comme une
        réponse à cette proposition (oui/non/incertain) plutôt que comme un
        nouveau tour de diagnostic.
        """

        active_ticket: Ticket | None = None
        awaiting_confirmation = False

        if conversation_id is not None:
            active_ticket = await self._ticket_service.get_active_ticket_by_conversation(conversation_id)
            if active_ticket is None:
                conversation = await self._chat_service.get_conversation(conversation_id, user.id)
                awaiting_confirmation = conversation.pending_ticket_confirmation

        if awaiting_confirmation:
            return await self._handle_confirmation_turn(user, content, conversation_id, product_id)

        return await self._handle_diagnostic_turn(user, content, conversation_id, product_id, active_ticket)

    async def _handle_diagnostic_turn(
        self,
        user: User,
        content: str,
        conversation_id: UUID | None,
        product_id: UUID | None,
        active_ticket: Ticket | None,
    ) -> DiagnosticResult:
        """Tour de diagnostic normal : détermine RESOLU / EN_COURS / A_ESCALADER.

        Sur A_ESCALADER : si un ticket actif existe déjà pour cette conversation,
        il est simplement réutilisé (pas de nouvelle proposition, pas de doublon).
        Sinon, le ticket n'est PAS créé : la conversation est marquée en attente
        de confirmation (`pending_ticket_confirmation = True`), le client étant
        déjà invité à confirmer par le texte de la réponse elle-même (cf.
        `DIAGNOSTIC_STATUS_INSTRUCTION`).
        """

        is_first_exchange = await self._is_first_user_message(conversation_id, user.id)

        conversation, assistant_message = await self._chat_service.send_message(
            user,
            content,
            conversation_id=conversation_id,
            product_id=product_id,
            extra_system_instructions=DIAGNOSTIC_STATUS_INSTRUCTION,
        )

        cleaned_content, status = _extract_status(assistant_message.content)

        if is_first_exchange and status is DiagnosticStatus.ESCALATE:
            status = DiagnosticStatus.IN_PROGRESS

        content_changed = cleaned_content != assistant_message.content
        if content_changed:
            assistant_message.content = cleaned_content
            self.session.add(assistant_message)

        ticket = active_ticket
        proposing_ticket = status is DiagnosticStatus.ESCALATE and active_ticket is None
        if proposing_ticket:
            conversation.pending_ticket_confirmation = True
            self.session.add(conversation)

        if content_changed or proposing_ticket:
            await self.session.commit()
            await self.session.refresh(assistant_message)
            if proposing_ticket:
                await self.session.refresh(conversation)

        return DiagnosticResult(conversation=conversation, message=assistant_message, status=status, ticket=ticket)

    async def _handle_confirmation_turn(
        self,
        user: User,
        content: str,
        conversation_id: UUID,
        product_id: UUID | None,
    ) -> DiagnosticResult:
        """Tour de confirmation : interprète la réponse du client à une proposition de ticket déjà faite.

        OUI       -> création réelle du ticket (TicketService, réutilisé sans duplication). La
                     description reprend l'échange qui a déclenché la proposition (le problème
                     réel), pas ce tour de confirmation lui-même (qui ne fait que dire "oui").
        NON       -> aucun ticket, l'attente de confirmation est levée, l'échange continue.
        INCERTAIN -> aucun ticket, l'attente de confirmation reste active (marqueur absent ou
                     réponse ambiguë retombent tous les deux sur ce cas, par prudence).
        """

        # Capturé tout de suite : après un rollback plus loin (échec de création de ticket),
        # `user` est expiré par SQLAlchemy et relire `user.id` déclencherait un lazy-load
        # synchrone hors contexte greenlet (MissingGreenlet). Un UUID simple reste valide.
        user_id = user.id

        # Capturé avant le tour de confirmation lui-même : c'est cet échange (la description du
        # problème et la proposition de ticket qui a suivi) qui doit alimenter le ticket, pas la
        # réponse "oui" du client.
        history_before = await self._chat_service.get_history(conversation_id, user_id)
        proposal_user_content, proposal_assistant_content = _last_exchange(history_before)

        conversation, assistant_message = await self._chat_service.send_message(
            user,
            content,
            conversation_id=conversation_id,
            product_id=product_id,
            extra_system_instructions=TICKET_CONFIRMATION_INSTRUCTION,
        )

        cleaned_content, answer = _extract_confirmation(assistant_message.content)

        content_changed = cleaned_content != assistant_message.content
        if content_changed:
            assistant_message.content = cleaned_content
            self.session.add(assistant_message)

        ticket: Ticket | None = None

        if answer is TicketConfirmation.CONFIRMED:
            try:
                ticket = await self._get_or_create_ticket(
                    user, conversation, proposal_user_content, proposal_assistant_content, product_id
                )
            except Exception:
                # La création du ticket est l'action métier elle-même (pas un enrichissement
                # optionnel) : si elle échoue, on ne doit surtout pas dire au client que son
                # ticket est créé. `pending_ticket_confirmation` n'a jamais été mis à False avec
                # succès (rollback), donc le prochain message sera de nouveau traité comme une
                # tentative de confirmation — même règle métier, le client peut simplement
                # redire "oui" pour réessayer.
                logger.error(
                    "Ticket confirmation: ticket creation failed UNEXPECTEDLY after client confirmation",
                    exc_info=True,
                )
                await self.session.rollback()
                # Après rollback, les objets déjà chargés sont expirés : on relit `conversation`
                # proprement plutôt que de réutiliser la référence précédente. Le texte de repli
                # n'est délibérément PAS recommit ici (un nouveau commit juste après un rollback,
                # sur cette même session, s'est avéré instable en pratique) : seule la réponse
                # immédiate au client reflète l'échec ; l'historique conserve le texte original
                # du LLM. Le prochain message du client relance normalement la confirmation.
                conversation = await self._chat_service.get_conversation(conversation_id, user_id)
                assistant_message.content = _TICKET_CREATION_FAILURE_MESSAGE
                return DiagnosticResult(
                    conversation=conversation,
                    message=assistant_message,
                    status=DiagnosticStatus.ESCALATE,
                    ticket=None,
                )

            status = DiagnosticStatus.ESCALATE
            conversation.pending_ticket_confirmation = False
            self.session.add(conversation)
        elif answer is TicketConfirmation.DECLINED:
            status = DiagnosticStatus.IN_PROGRESS
            conversation.pending_ticket_confirmation = False
            self.session.add(conversation)
            await self.session.commit()
            await self.session.refresh(conversation)
            await self.session.refresh(assistant_message)
        else:
            status = DiagnosticStatus.ESCALATE
            if content_changed:
                await self.session.commit()
                await self.session.refresh(assistant_message)

        return DiagnosticResult(conversation=conversation, message=assistant_message, status=status, ticket=ticket)

    async def _get_or_create_ticket(
        self,
        user: User,
        conversation: Conversation,
        user_content: str,
        assistant_content: str,
        product_id: UUID | None,
    ) -> Ticket:
        """Réutilise le ticket actif de la conversation s'il existe, sinon en crée un.

        Le titre reprend celui déjà généré pour la conversation (ChatService).
        La description et l'identification du produit sont générées par un
        appel LLM dédié (`_synthesize_ticket_description_and_product`),
        uniquement lorsqu'un ticket est réellement sur le point d'être créé
        (jamais pour un ticket réutilisé).
        """

        existing = await self._ticket_service.get_active_ticket_by_conversation(conversation.id)
        if existing is not None:
            return existing

        description, resolved_product_id = await self._synthesize_ticket_description_and_product(
            user_content, assistant_content, product_id, user.preferred_language
        )

        data = TicketAutoCreate(
            title=conversation.title or _FALLBACK_TICKET_TITLE,
            description=description,
            product_id=resolved_product_id,
        )
        return await self._ticket_service.create_ticket(user, data, conversation_id=conversation.id)

    async def _synthesize_ticket_description_and_product(
        self, user_content: str, assistant_content: str, known_product_id: UUID | None, language: str
    ) -> tuple[str, UUID | None]:
        """Génère la description technique du ticket et tente d'identifier le produit concerné.

        Réutilise le RAG existant (`RetrieverService.retrieve`, exactement la
        même méthode que le reste de l'application, aucune nouvelle heuristique
        de détection produit) : `ChatService.send_message` ne retourne jamais
        les chunks qu'il a retrouvés pendant le tour de diagnostic qui a
        déclenché l'escalade (ils restent internes à cette méthode), donc ils
        ne peuvent pas être réutilisés tels quels sans modifier ChatService.
        Un nouvel appel, avec la même méthode et le même texte de requête,
        est donc nécessaire ici — mais une seule fois, seulement au moment
        réel de la création du ticket (jamais par tour de conversation, jamais
        pour un ticket réutilisé).

        `language` (typiquement `user.preferred_language`) détermine la langue
        de la description générée ; le marqueur `[PRODUIT: ...]` reste stable
        et parsable indépendamment de la langue.

        Purement optionnel, en trois étapes indépendantes, chacune avec son
        propre repli — une erreur d'enrichissement n'empêche jamais la
        création du ticket :
        1. Recherche RAG : si elle échoue, la synthèse continue sans contexte
           documentaire (même philosophie que `ChatService._retrieve_context`).
        2. Appel LLM de synthèse : s'il échoue, repli sur une description
           statique/hybride (`_build_fallback_description`).
        3. Résolution du produit en base : si elle échoue après une synthèse
           LLM réussie, la description LLM est conservée et `product_id` reste
           `None`.
        """

        fallback_description = _build_fallback_description(user_content, assistant_content)

        chunks: list[RetrievedChunk] = []
        try:
            chunks = await self._retriever.retrieve(user_content, product_id=known_product_id)
        except EmbeddingError:
            logger.warning(
                "Ticket synthesis: RAG retrieval failed (embedding/vector store), continuing without context",
                exc_info=True,
            )
        except Exception:
            logger.error(
                "Ticket synthesis: RAG retrieval failed UNEXPECTEDLY, continuing without context",
                exc_info=True,
            )

        try:
            system_prompt = build_ticket_synthesis_instruction(language) + build_context_section(chunks)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ]
            raw_synthesis = await self._llm_service.generate_reply(messages)
        except LLMError:
            logger.warning(
                "Ticket synthesis: LLM call failed, falling back to a plain description", exc_info=True
            )
            return fallback_description, known_product_id
        except Exception:
            logger.error(
                "Ticket synthesis: LLM call failed UNEXPECTEDLY, falling back to a plain description",
                exc_info=True,
            )
            return fallback_description, known_product_id

        description, product_identifier = _extract_product_and_description(raw_synthesis)
        if not description:
            description = fallback_description
        description = _truncate_description(description)

        resolved_product_id = known_product_id
        if resolved_product_id is None and product_identifier:
            try:
                resolved_product_id = await self._resolve_product_id(product_identifier, chunks)
            except Exception:
                logger.error(
                    "Ticket synthesis: product resolution failed UNEXPECTEDLY, keeping the LLM "
                    "description but leaving product_id unset",
                    exc_info=True,
                )
                resolved_product_id = None

        return description, resolved_product_id

    async def _resolve_product_id(self, identifier: str, chunks: list[RetrievedChunk]) -> UUID | None:
        """Recherche un produit par référence exacte, puis par nom exact (insensible à la casse).

        N'accepte la résolution que si le produit trouvé est également
        corroboré par le contenu/titre d'au moins un chunk RAG utilisé pour
        cette synthèse (règle validée) : réduit le risque qu'une
        identification plausible mais erronée du LLM ne pointe, par simple
        coïncidence, vers un vrai produit sans rapport avec le contexte
        réellement fourni. Aucune recherche approximative, aucun ID deviné.
        """

        product_service = ProductService(self.session)

        product = await product_service.get_product_by_reference(identifier)
        if product is None:
            product = await product_service.get_product_by_name(identifier)

        if product is None:
            return None

        corroborated = _reference_corroborated(product.reference, chunks) or _name_corroborated(
            product.name, chunks
        )

        return product.id if corroborated else None

    async def _is_first_user_message(self, conversation_id: UUID | None, user_id: UUID) -> bool:
        """Vrai si `conversation_id` est absent (nouvelle conversation) ou ne contient encore aucun message."""

        if conversation_id is None:
            return True

        history = await self._chat_service.get_history(conversation_id, user_id)
        return len(history) == 0


def _extract_status(content: str) -> tuple[str, DiagnosticStatus]:
    """Extrait le marqueur de statut de fin de réponse.

    Si le LLM a omis le marqueur ou l'a mal formé, on retombe sur EN_COURS
    plutôt que de faire échouer le diagnostic : mieux vaut continuer la
    conversation que d'escalader par erreur sur un défaut de formatage.
    """

    match = _STATUS_MARKER_PATTERN.search(content)
    if match is None:
        return content, DiagnosticStatus.IN_PROGRESS

    cleaned = content[: match.start()].rstrip()
    status = DiagnosticStatus(DIAGNOSTIC_STATUS_MARKERS[match.group(1)])
    return cleaned, status


def _last_exchange(history: list[Message]) -> tuple[str, str]:
    """Retourne (dernier message utilisateur, dernier message assistant) trouvés dans `history`.

    Utilisé pour retrouver l'échange qui a déclenché une proposition de ticket
    (juste avant le tour de confirmation), quel que soit l'ordre exact des
    rôles en fin d'historique.
    """

    last_user_content = ""
    last_assistant_content = ""

    for message in reversed(history):
        if message.role == "assistant" and not last_assistant_content:
            last_assistant_content = message.content
        elif message.role == "user" and not last_user_content:
            last_user_content = message.content

        if last_user_content and last_assistant_content:
            break

    return last_user_content, last_assistant_content


def _build_fallback_description(user_content: str, assistant_content: str) -> str:
    """Description de repli utilisée quand la synthèse LLM échoue.

    Combine une phrase statique standard (jamais d'erreur technique ni de
    trace d'exception) avec l'échange réel qui a déclenché l'escalade, pour
    rester utile au technicien même sans enrichissement LLM.
    """

    return _truncate_description(
        f"{_FALLBACK_TICKET_DESCRIPTION_PREFIX}\n\n"
        f"Question du client : {user_content}\n\n"
        f"Réponse du diagnostic automatique : {assistant_content}"
    )


def _normalize_reference(value: str) -> str:
    """Normalise une référence produit : casse et séparateurs cosmétiques (espace, tiret,
    underscore) ignorés. Les caractères alphanumériques eux-mêmes ne sont jamais altérés
    (aucune distance d'édition, aucune tolérance de faute de frappe)."""

    return _NON_ALNUM_PATTERN.sub("", value.lower())


def _reference_candidates(text: str, *, max_words: int = _MAX_WORDS_FOR_REFERENCE_MATCH) -> set[str]:
    """Combinaisons normalisées de 1 à `max_words` mots CONSÉCUTIFS de `text`.

    Permet de reconnaître une référence écrite avec des espaces à la place de
    tirets (ex. "IMP X100" ~ "IMP-X100") sans jamais fusionner des mots non
    adjacents ni tout le texte du document en un seul bloc — ce qui
    réintroduirait un risque de coïncidence accidentelle sur une référence
    courte (recherche approximative interdite par la règle validée).
    """

    words = text.split()
    candidates: set[str] = set()
    for start in range(len(words)):
        for length in range(1, max_words + 1):
            group = words[start : start + length]
            if len(group) < length:
                break
            candidates.add(_normalize_reference("".join(group)))
    return candidates


def _reference_corroborated(reference: str, chunks: list[RetrievedChunk]) -> bool:
    """Vrai si `reference` (normalisée) correspond exactement à une combinaison de mots
    consécutifs d'au moins un chunk. Sous MIN_REFERENCE_LENGTH_FOR_MATCH caractères
    normalisés : jamais corroboré, trop court/générique pour être distingué de façon fiable."""

    normalized = _normalize_reference(reference)
    if len(normalized) < MIN_REFERENCE_LENGTH_FOR_MATCH:
        return False

    return any(normalized in _reference_candidates(f"{chunk.title} {chunk.text}") for chunk in chunks)


def _normalize_phrase(value: str) -> str:
    """Normalise une phrase (nom de produit) : casse et espaces multiples uniquement.
    Les mots eux-mêmes ne sont jamais altérés (aucune recherche approximative)."""

    return " ".join(value.lower().split())


def _name_corroborated(name: str, chunks: list[RetrievedChunk]) -> bool:
    """Vrai si `name` (normalisé) apparaît comme sous-phrase dans le titre/texte d'un chunk."""

    normalized = _normalize_phrase(name)
    if len(normalized) < MIN_NAME_LENGTH_FOR_MATCH:
        return False

    return any(normalized in _normalize_phrase(f"{chunk.title} {chunk.text}") for chunk in chunks)


def _extract_product_and_description(content: str) -> tuple[str, str | None]:
    """Extrait le marqueur produit de fin de réponse ainsi que la description qui précède.

    Retourne `(description, None)` si le marqueur est absent, mal formé, vide
    ou vaut explicitement AUCUN : jamais d'identifiant fantôme en cas de doute
    (résolution réelle en base déléguée à `_resolve_product_id`).
    """

    match = _PRODUCT_MARKER_PATTERN.search(content)
    if match is None:
        return content.strip(), None

    description = content[: match.start()].rstrip()
    identifier = match.group(1).strip()

    if not identifier or identifier.upper() == "AUCUN":
        return description, None

    return description, identifier


def _truncate_description(description: str, *, max_length: int = TICKET_DESCRIPTION_MAX_LENGTH) -> str:
    """Plafonne la longueur d'une description, au dernier mot entier (jamais coupé en plein mot).

    Même style que `ai.llm._clean_title` : filet de sécurité technique,
    complémentaire à la consigne de longueur du prompt.
    """

    stripped = description.strip()
    if len(stripped) <= max_length:
        return stripped

    truncated = stripped[:max_length].rsplit(" ", 1)[0].rstrip(".,;:!?")
    return f"{truncated}…" if truncated else stripped[:max_length]


def _extract_confirmation(content: str) -> tuple[str, TicketConfirmation]:
    """Extrait le marqueur de confirmation de fin de réponse.

    Si le LLM a omis le marqueur ou l'a mal formé, on retombe sur UNCLEAR :
    par prudence, l'absence de confirmation claire ne doit jamais déclencher
    la création d'un ticket (même principe que `_extract_status`).
    """

    match = _CONFIRMATION_MARKER_PATTERN.search(content)
    if match is None:
        return content, TicketConfirmation.UNCLEAR

    cleaned = content[: match.start()].rstrip()
    answer = TicketConfirmation(TICKET_CONFIRMATION_MARKERS[match.group(1)])
    return cleaned, answer


__all__ = ["TICKET_DESCRIPTION_MAX_LENGTH", "DiagnosticResult", "DiagnosticService"]
