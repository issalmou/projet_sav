"""add pending_ticket_confirmation to conversations

Revision ID: 9c4d7a1f6e83
Revises: e168dfe1c65a
Create Date: 2026-08-22 02:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c4d7a1f6e83'
down_revision = 'e168dfe1c65a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'conversations',
        sa.Column(
            'pending_ticket_confirmation',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column('conversations', 'pending_ticket_confirmation')
