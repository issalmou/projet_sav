"""add required purchase date to client_products"""
from alembic import op
import sqlalchemy as sa


revision = "f4a6b8c2d1e0"
down_revision = "d3d5a9319922"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_products",
        sa.Column("purchase_date", sa.Date(), nullable=True),
    )
    op.execute("UPDATE client_products SET purchase_date = CURRENT_DATE WHERE purchase_date IS NULL")
    op.alter_column("client_products", "purchase_date", nullable=False)


def downgrade() -> None:
    op.drop_column("client_products", "purchase_date")