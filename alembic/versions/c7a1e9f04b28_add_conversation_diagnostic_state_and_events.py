"""add conversation diagnostic state and conversation_events

Revision ID: c7a1e9f04b28
Revises: d3d5a9319922
Create Date: 2026-09-11

Résolution interactive multi-tour (workflow CDC §14/§17) :

- `conversations` reçoit 4 colonnes d'état DÉTERMINISTE du diagnostic
  (`diagnostic_attempts`, `search_performed`, `awaiting_step_feedback`,
  `problem_resolved`). Toutes `NOT NULL` avec `server_default` → les lignes
  existantes prennent la valeur neutre (0 / false). Aucune donnée touchée.

- `conversation_events` : journal append-only du diagnostic (recherche,
  hypothèse + étapes, retour client, escalade, ticket). `payload` en JSONB
  (PostgreSQL). `ON DELETE CASCADE` : dérivé de la conversation.

Migration NON destructive et réversible.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c7a1e9f04b28'
down_revision = 'd3d5a9319922'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'conversations',
        sa.Column('diagnostic_attempts', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'conversations',
        sa.Column('search_performed', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'conversations',
        sa.Column('awaiting_step_feedback', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'conversations',
        sa.Column('problem_resolved', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        'conversation_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=32), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['conversation_id'], ['conversations.id'],
            name=op.f('fk_conversation_events_conversation_id_conversations'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_conversation_events')),
        sa.CheckConstraint(
            "event_type IN ('search', 'diagnosis', 'feedback', 'escalation', 'ticket')",
            name=op.f('ck_conversation_events_event_type_valid'),
        ),
    )
    op.create_index(
        op.f('ix_conversation_events_conversation_id'),
        'conversation_events',
        ['conversation_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_conversation_events_conversation_id'), table_name='conversation_events')
    op.drop_table('conversation_events')
    op.drop_column('conversations', 'problem_resolved')
    op.drop_column('conversations', 'awaiting_step_feedback')
    op.drop_column('conversations', 'search_performed')
    op.drop_column('conversations', 'diagnostic_attempts')
