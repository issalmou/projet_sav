"""Tests de ai/rag/loader.py : extraction de texte PDF/DOCX/TXT (semaine 4, tâche 4)."""
from pathlib import Path

import pytest

from app.ai.rag.loader import DocumentLoadError, DocumentLoader

KNOWLEDGE_BASE_PRODUCTS = Path(__file__).resolve().parents[1] / "knowledge_base" / "products"


def _minimal_pdf_bytes(text: str) -> bytes:
    """Construit un PDF minimal valide contenant `text`, sans dépendance externe (fixture de test)."""

    content = f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 200 200] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]

    buffer = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(buffer))
        buffer += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_offset = len(buffer)
    buffer += f"xref\n0 {len(objects) + 1}\n".encode()
    buffer += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        buffer += f"{offset:010} 00000 n \n".encode()
    buffer += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()

    return bytes(buffer)


@pytest.fixture
def loader() -> DocumentLoader:
    return DocumentLoader()


def test_extract_text_from_real_docx(loader):
    """Extraction sur un vrai document métier fourni par l'utilisateur (pas de contenu fabriqué)."""

    source = KNOWLEDGE_BASE_PRODUCTS / "Prime Châssis en Wallonie 2026.docx"
    assert source.exists(), "Document réel manquant dans knowledge_base/products/"

    text = loader.load_text(source, "docx")

    assert "Châssis" in text
    assert "wallonne" in text


def test_extract_text_from_txt(loader, tmp_path):
    path = tmp_path / "guide.txt"
    path.write_text("Vérifiez le capteur papier.", encoding="utf-8")

    text = loader.load_text(path, "txt")

    assert text == "Vérifiez le capteur papier."


def test_extract_text_from_pdf(loader, tmp_path):
    path = tmp_path / "guide.pdf"
    path.write_bytes(_minimal_pdf_bytes("Hello RAG"))

    text = loader.load_text(path, "pdf")

    assert "Hello RAG" in text


def test_missing_file_raises(loader, tmp_path):
    with pytest.raises(DocumentLoadError):
        loader.load_text(tmp_path / "absent.txt", "txt")


def test_unsupported_file_type_raises(loader, tmp_path):
    path = tmp_path / "guide.rtf"
    path.write_text("contenu", encoding="utf-8")

    with pytest.raises(DocumentLoadError):
        loader.load_text(path, "rtf")


def test_empty_file_raises(loader, tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("   \n", encoding="utf-8")

    with pytest.raises(DocumentLoadError):
        loader.load_text(path, "txt")


__all__: list[str] = []
