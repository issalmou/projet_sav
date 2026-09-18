"""merge purchase_date branch with main branch

Revision ID: a08f8340fd00
Revises: b7e2f4a1c9d6, f4a6b8c2d1e0
Create Date: 2026-09-18 00:09:21.366732
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a08f8340fd00'
down_revision = ('b7e2f4a1c9d6', 'f4a6b8c2d1e0')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
