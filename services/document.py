"""Services liés aux documents (base de connaissances / RAG)."""
import asyncio
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.embedding_service import EmbeddingService
from app.ai.exceptions import EmbeddingError
from app.ai.rag.chunker import Chunk, ChunkService
from app.ai.rag.loader import DocumentLoadError, DocumentLoader
from app.ai.rag.vector_store import VectorStore
from app.core.config import settings
from app.core.logger import logger
from app.database.base import utcnow
from app.models.document import Document, DocumentProduct
from app.models.product import Product
from app.models.user import User
from app.schemas.document import DocumentUploadMetadata
from app.utils.constants import DocumentType


class UnsupportedFileTypeError(ValueError):
    """Le format du fichier n'est pas parmi ceux autorisés (pdf, docx, txt)."""


class FileTooLargeError(ValueError):
    """Le fichier dépasse la taille maximale autorisée."""


class ProductNotFoundError(ValueError):
    """Un `product_id` fourni ne correspond à aucun produit existant."""


class DocumentPermissionError(Exception):
    """L'utilisateur a le rôle Responsable SAV mais n'est pas le créateur de ce document précis.

    Distinct de `ValueError` (document introuvable) : mappé sur 403, pas 404
    — le document existe et est visible, mais cet utilisateur ne peut pas le
    modifier (validation métier du 2026-08-08 : chaque Responsable SAV ne
    gère que les documents qu'il a lui-même ajoutés, sauf superuser).
    """


class DocumentIndexingError(Exception):
    """L'indexation RAG a échoué après la création du document : l'upload entier est annulé.

    Décision métier validée : l'indexation est obligatoire pour qu'un upload
    soit considéré comme réussi. Le message d'origine (DocumentLoadError,
    EmbeddingError, ou toute exception inattendue) est chaîné via `__cause__`
    pour les logs, mais jamais exposé au client — la route ne doit renvoyer
    qu'un message générique (500).
    """


class DocumentService:
    """Orchestrateur métier pour les documents."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        embedder: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.session = session
        self._loader = DocumentLoader()
        self._chunker = ChunkService()
        self._embedder = embedder
        self._vector_store = vector_store

    async def list_documents(self, current_user: User) -> list[Document]:
        """Liste les documents du Responsable SAV courant (tous les documents pour un superuser)."""

        query = select(Document).options(selectinload(Document.created_by)).order_by(Document.created_at.desc())
        if not current_user.is_superuser:
            query = query.where(Document.created_by_id == current_user.id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def upload_document(
        self, *, file: UploadFile, metadata: DocumentUploadMetadata, created_by: User
    ) -> Document:
        """Valide le format, sauvegarde le fichier, enregistre le document ET l'indexe pour le RAG.

        L'indexation est obligatoire pour qu'un upload soit considéré comme
        réussi (décision métier validée) : aucun fallback ici, contrairement à
        la synthèse de ticket. Si `index_document` échoue pour quelque raison
        que ce soit, TOUT est annulé — rollback PostgreSQL (le document
        n'existe jamais côté base, `flush()` remplace le `commit()` précédent
        pour permettre ce rollback classique), nettoyage best-effort d'éventuels
        chunks déjà écrits dans le VectorStore, et suppression du fichier
        physique déjà présent sur disque. Aucun artefact partiel ne doit
        survivre à un échec (ni ligne PostgreSQL, ni fichier orphelin).
        """

        file_type = _resolve_file_type(file.filename)

        content = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise FileTooLargeError(f"File exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB")

        products = await self._get_products_or_raise(metadata.product_ids)

        stored_path = settings.UPLOAD_DIR / f"{uuid.uuid4()}.{file_type.value}"
        await _write_file(stored_path, content)

        document = Document(
            title=metadata.title,
            file_type=file_type.value,
            category=metadata.category.value,
            version=metadata.version,
            file_name=file.filename or stored_path.name,
            file_path=str(stored_path),
            file_size=len(content),
            created_by_id=created_by.id,
            products=products,
        )
        self.session.add(document)
        # flush (pas commit) : alloue document.id et écrit les lignes document_products dans la
        # transaction en cours, sans la valider — index_document() en a besoin (product_ids,
        # upsert VectorStore), mais un rollback classique reste possible tant que rien n'est commit.
        await self.session.flush()
        document_id = document.id  # capturé avant un éventuel rollback (qui expire l'objet)

        try:
            await self.index_document(document)
        except (DocumentLoadError, EmbeddingError) as exc:
            logger.warning(
                "Document upload aborted: indexing failed (%s), rolling back and cleaning up",
                type(exc).__name__,
                exc_info=True,
            )
            await self._rollback_failed_upload(document_id, stored_path)
            raise DocumentIndexingError("Document indexing failed") from exc
        except Exception as exc:
            logger.error(
                "Document upload aborted: indexing failed UNEXPECTEDLY, rolling back and cleaning up",
                exc_info=True,
            )
            await self._rollback_failed_upload(document_id, stored_path)
            raise DocumentIndexingError("Document indexing failed unexpectedly") from exc

        await self.session.refresh(document, attribute_names=["products", "created_by"])
        return document

    async def _rollback_failed_upload(self, document_id: UUID, stored_path: Path) -> None:
        """Annule un upload dont l'indexation a échoué.

        Rollback PostgreSQL (document + associations document_products jamais
        commit, donc réellement absents après coup) ; nettoyage best-effort du
        VectorStore (au cas où des chunks auraient été partiellement écrits
        avant l'échec) ; suppression du fichier physique déjà écrit sur disque.
        Ne lève jamais elle-même : un échec de nettoyage ne doit pas masquer
        l'erreur d'indexation d'origine.
        """

        await self.session.rollback()

        try:
            await asyncio.to_thread(self._get_vector_store().delete_document_chunks, document_id)
        except Exception:
            logger.error(
                "Cleanup: failed to remove partial VectorStore chunks for document %s", document_id, exc_info=True
            )

        try:
            if stored_path.exists():
                await asyncio.to_thread(stored_path.unlink)
        except Exception:
            logger.error("Cleanup: failed to remove orphaned file %s", stored_path, exc_info=True)

    async def index_document(self, document: Document) -> list[Chunk] | None:
        """Indexe `document` pour le RAG (extraction, chunking, embeddings, stockage vectoriel)."""

        if document.indexed_at is not None:
            return None

        text = self._loader.load_text(document.file_path, document.file_type)
        chunks = self._chunker.split_text(text)

        if chunks:
            embeddings = await self._get_embedder().embed_texts([chunk.text for chunk in chunks])
            product_ids_result = await self.session.execute(
                select(DocumentProduct.product_id).where(DocumentProduct.document_id == document.id)
            )
            product_ids = list(product_ids_result.scalars().all())

            await asyncio.to_thread(
                self._get_vector_store().upsert_document_chunks,
                document_id=document.id,
                title=document.title,
                category=document.category,
                product_ids=product_ids,
                chunks=chunks,
                embeddings=embeddings,
            )

        document.indexed_at = utcnow()
        self.session.add(document)
        await self.session.commit()

        return chunks

    async def index_pending_documents(self) -> dict[UUID, list[Chunk]]:
        """Indexe tous les documents pas encore traités (`indexed_at IS NULL`)."""

        result = await self.session.execute(select(Document).where(Document.indexed_at.is_(None)))
        pending = list(result.scalars().all())

        processed: dict[UUID, list[Chunk]] = {}
        for document in pending:
            try:
                chunks = await self.index_document(document)
            except (DocumentLoadError, EmbeddingError) as exc:
                logger.warning("Skipping document %s during indexing: %s", document.id, exc)
                continue

            if chunks is not None:
                processed[document.id] = chunks

        return processed

    async def delete_document(self, document_id: UUID, current_user: User) -> None:
        """Supprime un document : ligne PostgreSQL, chunks ChromaDB, fichier physique.

        Chaque Responsable SAV ne peut supprimer que les documents qu'il a
        lui-même ajoutés (`created_by_id`), sauf superuser qui peut tout
        supprimer — comme pour les autres capacités de gestion des comptes
        déjà en place (`can_manage_role`). Les associations `DocumentProduct`
        sont supprimées en cascade par la base (`ondelete="CASCADE"`).
        """

        document = await self.session.get(Document, document_id)
        if document is None:
            raise ValueError("Document not found")

        if document.created_by_id != current_user.id and not current_user.is_superuser:
            raise DocumentPermissionError("You can only delete documents you created")

        file_path = Path(document.file_path)

        await asyncio.to_thread(self._get_vector_store().delete_document_chunks, document_id)

        await self.session.delete(document)
        await self.session.commit()

        if file_path.exists():
            await asyncio.to_thread(file_path.unlink)

    def _get_embedder(self) -> EmbeddingService:
        if self._embedder is None:
            self._embedder = EmbeddingService()
        return self._embedder

    def _get_vector_store(self) -> VectorStore:
        if self._vector_store is None:
            self._vector_store = VectorStore()
        return self._vector_store

    async def _get_products_or_raise(self, product_ids: list[UUID]) -> list[Product]:
        if not product_ids:
            return []

        result = await self.session.execute(select(Product).where(Product.id.in_(product_ids)))
        products = list(result.scalars().all())

        missing = set(product_ids) - {product.id for product in products}
        if missing:
            raise ProductNotFoundError(f"Unknown product id(s): {', '.join(str(pid) for pid in missing)}")

        return products


def _resolve_file_type(filename: str | None) -> DocumentType:
    suffix = Path(filename or "").suffix.lower().lstrip(".")
    try:
        return DocumentType(suffix)
    except ValueError:
        allowed = ", ".join(item.value for item in DocumentType)
        raise UnsupportedFileTypeError(f"Unsupported file type '{suffix}'. Allowed: {allowed}") from None


async def _write_file(path: Path, content: bytes) -> None:
    def _write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    await asyncio.to_thread(_write)


__all__ = [
    "DocumentIndexingError",
    "DocumentPermissionError",
    "DocumentService",
    "FileTooLargeError",
    "ProductNotFoundError",
    "UnsupportedFileTypeError",
]
