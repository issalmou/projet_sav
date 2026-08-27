"""Tests de ai/rag/vector_store.py : stockage ChromaDB (semaine 4, tâche 7)."""
import uuid

import pytest

from app.ai.rag.chunker import Chunk
from app.ai.rag.vector_store import VectorStore


@pytest.fixture
def store(tmp_path) -> VectorStore:
    return VectorStore(persist_directory=tmp_path / "chroma")


def test_upsert_stores_chunks_with_embeddings_and_metadata(store):
    document_id = uuid.uuid4()
    chunks = [Chunk(index=0, text="Premier chunk"), Chunk(index=1, text="Deuxième chunk")]

    store.upsert_document_chunks(
        document_id=document_id,
        title="Guide erreur E17",
        category="faq",
        product_ids=[],
        chunks=chunks,
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
    )

    assert store.count() == 2
    texts = store.get_document_chunks(document_id)
    assert set(texts) == {"Premier chunk", "Deuxième chunk"}


def test_upsert_stores_product_ids_as_metadata(store):
    document_id = uuid.uuid4()
    product_id = uuid.uuid4()

    store.upsert_document_chunks(
        document_id=document_id,
        title="Notice produit",
        category="products",
        product_ids=[product_id],
        chunks=[Chunk(index=0, text="Contenu")],
        embeddings=[[0.1, 0.2]],
    )

    metadatas = store.get_document_chunk_metadatas(document_id)
    assert metadatas[0]["product_ids"] == [str(product_id)]


def test_general_document_has_no_product_ids_key(store):
    """ChromaDB rejette les métadonnées liste vides : la clé est omise, pas vide."""

    document_id = uuid.uuid4()

    store.upsert_document_chunks(
        document_id=document_id,
        title="Document général",
        category="faq",
        product_ids=[],
        chunks=[Chunk(index=0, text="Contenu")],
        embeddings=[[0.1, 0.2]],
    )

    metadatas = store.get_document_chunk_metadatas(document_id)
    assert "product_ids" not in metadatas[0]


def test_upsert_is_idempotent_for_the_same_chunk_ids(store):
    document_id = uuid.uuid4()
    chunk = Chunk(index=0, text="Version initiale")

    store.upsert_document_chunks(
        document_id=document_id, title="T", category="faq", product_ids=[], chunks=[chunk], embeddings=[[0.1]]
    )
    store.upsert_document_chunks(
        document_id=document_id,
        title="T",
        category="faq",
        product_ids=[],
        chunks=[Chunk(index=0, text="Version mise à jour")],
        embeddings=[[0.2]],
    )

    assert store.count() == 1
    assert store.get_document_chunks(document_id) == ["Version mise à jour"]


def test_delete_document_chunks_removes_only_that_document(store):
    doc_a, doc_b = uuid.uuid4(), uuid.uuid4()
    for doc_id, text in [(doc_a, "chunk A"), (doc_b, "chunk B")]:
        store.upsert_document_chunks(
            document_id=doc_id,
            title="T",
            category="faq",
            product_ids=[],
            chunks=[Chunk(index=0, text=text)],
            embeddings=[[0.1]],
        )

    store.delete_document_chunks(doc_a)

    assert store.get_document_chunks(doc_a) == []
    assert store.get_document_chunks(doc_b) == ["chunk B"]


def test_upsert_with_mismatched_lengths_raises(store):
    with pytest.raises(ValueError):
        store.upsert_document_chunks(
            document_id=uuid.uuid4(),
            title="T",
            category="faq",
            product_ids=[],
            chunks=[Chunk(index=0, text="a"), Chunk(index=1, text="b")],
            embeddings=[[0.1]],
        )


def test_upsert_with_no_chunks_is_a_noop(store):
    store.upsert_document_chunks(
        document_id=uuid.uuid4(), title="T", category="faq", product_ids=[], chunks=[], embeddings=[]
    )

    assert store.count() == 0


def test_query_returns_nearest_chunk_first(store):
    store.upsert_document_chunks(
        document_id=uuid.uuid4(),
        title="Loin",
        category="faq",
        product_ids=[],
        chunks=[Chunk(index=0, text="chunk loin")],
        embeddings=[[10.0, 10.0]],
    )
    store.upsert_document_chunks(
        document_id=uuid.uuid4(),
        title="Proche",
        category="faq",
        product_ids=[],
        chunks=[Chunk(index=0, text="chunk proche")],
        embeddings=[[1.0, 1.0]],
    )

    results = store.query(query_embedding=[1.0, 1.0], n_results=2)

    assert results[0][0] == "chunk proche"
    assert results[0][2] < results[1][2]


def test_query_with_product_id_includes_general_documents_only(store):
    product_id = uuid.uuid4()
    other_product_id = uuid.uuid4()

    store.upsert_document_chunks(
        document_id=uuid.uuid4(),
        title="Produit ciblé",
        category="products",
        product_ids=[product_id],
        chunks=[Chunk(index=0, text="chunk produit cible")],
        embeddings=[[1.0, 0.0]],
    )
    store.upsert_document_chunks(
        document_id=uuid.uuid4(),
        title="Autre produit",
        category="products",
        product_ids=[other_product_id],
        chunks=[Chunk(index=0, text="chunk autre produit")],
        embeddings=[[1.0, 0.0]],
    )
    store.upsert_document_chunks(
        document_id=uuid.uuid4(),
        title="FAQ générale",
        category="faq",
        product_ids=[],
        chunks=[Chunk(index=0, text="chunk general")],
        embeddings=[[1.0, 0.0]],
    )

    results = store.query(query_embedding=[1.0, 0.0], n_results=10, product_id=product_id)
    texts = {text for text, _, _ in results}

    assert "chunk produit cible" in texts
    assert "chunk general" in texts
    assert "chunk autre produit" not in texts


def test_query_without_product_id_searches_globally(store):
    product_id = uuid.uuid4()
    store.upsert_document_chunks(
        document_id=uuid.uuid4(),
        title="Produit",
        category="products",
        product_ids=[product_id],
        chunks=[Chunk(index=0, text="chunk produit")],
        embeddings=[[1.0, 0.0]],
    )
    store.upsert_document_chunks(
        document_id=uuid.uuid4(),
        title="FAQ",
        category="faq",
        product_ids=[],
        chunks=[Chunk(index=0, text="chunk general")],
        embeddings=[[1.0, 0.0]],
    )

    results = store.query(query_embedding=[1.0, 0.0], n_results=10)
    texts = {text for text, _, _ in results}

    assert texts == {"chunk produit", "chunk general"}


__all__: list[str] = []
