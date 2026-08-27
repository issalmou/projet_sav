"""Tests de ai/rag/chunker.py : découpage de texte (semaine 4, tâche 5)."""
import pytest

from app.ai.rag.chunker import Chunk, ChunkService


def test_short_text_is_a_single_chunk():
    service = ChunkService(chunk_size=1000, chunk_overlap=150)

    chunks = service.split_text("Vérifiez le capteur papier.")

    assert chunks == [Chunk(index=0, text="Vérifiez le capteur papier.")]


def test_empty_or_whitespace_text_returns_no_chunks():
    service = ChunkService()

    assert service.split_text("") == []
    assert service.split_text("   \n\t  ") == []


def test_long_text_is_split_into_overlapping_chunks():
    service = ChunkService(chunk_size=50, chunk_overlap=10)
    words = [f"mot{i}" for i in range(60)]  # ~300 caractères, largement > chunk_size
    text = " ".join(words)

    chunks = service.split_text(text)

    assert len(chunks) > 1
    # aucun chunk ne dépasse la taille demandée
    assert all(len(chunk.text) <= 50 for chunk in chunks)
    # les index sont continus, à partir de 0
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    # chaque mot du texte source apparaît dans au moins un chunk (rien n'est perdu)
    joined = " ".join(chunk.text for chunk in chunks)
    for word in words:
        assert word in joined


def test_no_word_is_cut_in_the_middle():
    service = ChunkService(chunk_size=50, chunk_overlap=10)
    text = " ".join(f"motducoup{i}" for i in range(30))

    chunks = service.split_text(text)

    for chunk in chunks:
        for token in chunk.text.split():
            assert token.startswith("motducoup") or token == ""


def test_consecutive_chunks_overlap():
    service = ChunkService(chunk_size=50, chunk_overlap=15)
    text = " ".join(f"mot{i}" for i in range(40))

    chunks = service.split_text(text)

    assert len(chunks) > 1
    first_words = set(chunks[0].text.split())
    second_words = set(chunks[1].text.split())
    assert first_words & second_words, "les chunks consécutifs doivent partager du contexte"


@pytest.mark.parametrize("chunk_size,chunk_overlap", [(0, 0), (-10, 0), (100, 100), (100, 150)])
def test_invalid_configuration_is_rejected(chunk_size, chunk_overlap):
    with pytest.raises(ValueError):
        ChunkService(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


__all__: list[str] = []
