"""Extraction de texte brut à partir des fichiers déposés (PDF, DOCX, TXT)."""
from pathlib import Path

import pypdf
from docx import Document as DocxDocument

from app.utils.constants import DocumentType


class DocumentLoadError(ValueError):
    """Le texte n'a pas pu être extrait du fichier (absent, illisible ou vide)."""


class DocumentLoader:
    """Extrait le texte brut d'un fichier PDF, DOCX ou TXT."""

    def load_text(self, file_path: str | Path, file_type: str) -> str:
        """Lit `file_path` (de type `file_type`) et retourne son contenu textuel."""

        path = Path(file_path)
        if not path.exists():
            raise DocumentLoadError(f"File not found: {path}")

        try:
            resolved_type = DocumentType(file_type)
        except ValueError:
            allowed = ", ".join(item.value for item in DocumentType)
            raise DocumentLoadError(f"Unsupported file type '{file_type}'. Allowed: {allowed}") from None

        text = _EXTRACTORS[resolved_type](path)

        if not text.strip():
            raise DocumentLoadError(f"No extractable text found in {path.name}")

        return text


def _extract_pdf(path: Path) -> str:
    reader = pypdf.PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(path: Path) -> str:
    document = DocxDocument(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _extract_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


_EXTRACTORS = {
    DocumentType.PDF: _extract_pdf,
    DocumentType.DOCX: _extract_docx,
    DocumentType.TXT: _extract_txt,
}


__all__ = ["DocumentLoadError", "DocumentLoader"]
