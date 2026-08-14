"""rename documents.chunked_at to indexed_at

Revision ID: 3db91fb53553
Revises: 3e591515042c
Create Date: 2026-08-08 00:37:43.603186
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '3db91fb53553'
down_revision = '3e591515042c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename plutôt que drop+add (ce que l'autogénération avait produit) :
    # préserve les données existantes. La sémantique du champ s'étend au
    # même moment (tâche 7) : il marque désormais la fin du pipeline complet
    # (chunking + embedding + stockage vectoriel), pas seulement le chunking.
    op.alter_column('documents', 'chunked_at', new_column_name='indexed_at')
    op.execute("ALTER INDEX ix_documents_chunked_at RENAME TO ix_documents_indexed_at")
    # NOTE : l'autogénération détecte aussi des uq_*_id "manquants" sur
    # plusieurs tables — artefact connu sans rapport avec cette migration
    # (cf. migrations d279c865f6da et 3e591515042c). Volontairement exclu.


def downgrade() -> None:
    op.alter_column('documents', 'indexed_at', new_column_name='chunked_at')
    op.execute("ALTER INDEX ix_documents_indexed_at RENAME TO ix_documents_chunked_at")
