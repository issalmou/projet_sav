"""Découpage du texte en chunks, en vue de l'embedding."""
from dataclasses import dataclass

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150


@dataclass(frozen=True)
class Chunk:
    """Un fragment de texte découpé, avec sa position dans le document source."""

    index: int
    text: str


class ChunkService:
    """Découpe un texte en fragments chevauchants, prêts pour l'embedding."""

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> list[Chunk]:
        """Découpe `text` en chunks chevauchants, sans couper un mot en plein milieu."""

        normalized = " ".join(text.split())
        if not normalized:
            return []

        if len(normalized) <= self.chunk_size:
            return [Chunk(index=0, text=normalized)]

        chunks: list[Chunk] = []
        start = 0

        while start < len(normalized):
            end = min(start + self.chunk_size, len(normalized))

            # Ne pas couper un mot en fin de chunk : reculer jusqu'au dernier
            # espace, sauf en fin de texte (rien à préserver après) ou si
            # aucun espace n'existe dans la fenêtre.
            if end < len(normalized):
                boundary = normalized.rfind(" ", start, end)
                if boundary > start:
                    end = boundary

            chunks.append(Chunk(index=len(chunks), text=normalized[start:end].strip()))

            if end >= len(normalized):
                break

            # max(..., start + 1) garantit une progression, même si le recul
            # au dernier espace a ramené `end` tout près de `start` (mot très
            # long juste après un espace isolé).
            next_start = max(end - self.chunk_overlap, start + 1)

            # Ne pas non plus commencer le chunk suivant en plein milieu d'un
            # mot : avancer jusqu'au prochain espace si nécessaire.
            if next_start < len(normalized) and normalized[next_start - 1] != " ":
                boundary = normalized.find(" ", next_start)
                next_start = boundary + 1 if boundary != -1 else next_start

            start = next_start

        return chunks


__all__ = ["Chunk", "ChunkService", "DEFAULT_CHUNK_OVERLAP", "DEFAULT_CHUNK_SIZE"]
