"""Tests de app.ai.prompts : section de contexte RAG (semaine 4, tâche 10)."""
import uuid

from app.ai.prompts import LOW_CONFIDENCE_INSTRUCTION, build_context_section
from app.ai.rag.retriever import RetrievedChunk


def _chunk(text: str, title: str = "Guide erreur E17") -> RetrievedChunk:
    return RetrievedChunk(text=text, document_id=uuid.uuid4(), title=title, category="faq", distance=0.1)


def test_build_context_section_is_empty_without_chunks():
    assert build_context_section([]) == ""


def test_build_context_section_includes_chunk_text_and_title():
    section = build_context_section([_chunk("Vérifiez le capteur papier.", title="Guide E17")])

    assert "Guide E17" in section
    assert "Vérifiez le capteur papier." in section


def test_build_context_section_includes_all_chunks():
    section = build_context_section([_chunk("Premier extrait"), _chunk("Deuxième extrait")])

    assert "Premier extrait" in section
    assert "Deuxième extrait" in section


def test_low_confidence_instruction_mentions_product_model():
    assert "modèle" in LOW_CONFIDENCE_INSTRUCTION.lower()
    assert "produit" in LOW_CONFIDENCE_INSTRUCTION.lower()


__all__: list[str] = []
