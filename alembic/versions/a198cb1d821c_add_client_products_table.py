"""add client_products table

Revision ID: a198cb1d821c
Revises: 9c4d7a1f6e83
Create Date: 2026-09-08 23:42:06.306829
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a198cb1d821c'
down_revision = '9c4d7a1f6e83'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'client_products',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], name=op.f('fk_client_products_user_id_users'), ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['product_id'], ['products.id'], name=op.f('fk_client_products_product_id_products'), ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_client_products')),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_client_product'),
        # NB : pas de `UniqueConstraint('id')` séparée — redondante avec la PK,
        # PostgreSQL ne la matérialise pas. Les migrations antérieures la
        # déclaraient quand même (dérive `uq_*_id` documentée) ; on ne la
        # propage pas ici pour que la table colle exactement à son schéma réel.
    )
    op.create_index(op.f('ix_client_products_user_id'), 'client_products', ['user_id'], unique=False)
    op.create_index(op.f('ix_client_products_product_id'), 'client_products', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_client_products_product_id'), table_name='client_products')
    op.drop_index(op.f('ix_client_products_user_id'), table_name='client_products')
    op.drop_table('client_products')
