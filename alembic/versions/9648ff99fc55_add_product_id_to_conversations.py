"""add product_id to conversations

Revision ID: 9648ff99fc55
Revises: a198cb1d821c
Create Date: 2026-09-09

Une conversation SAV existe toujours dans le contexte d'un produit : la
colonne est NOT NULL. Migration en trois temps pour rester sûre même si des
conversations « héritées » (créées avant cette évolution) existent :

  1. ajout de la colonne en nullable + FK ON DELETE CASCADE ;
  2. suppression des conversations sans produit — elles ne peuvent, par
     construction, pas satisfaire le nouveau contrat (aucun produit à leur
     rattacher rétroactivement) ; leurs messages partent en cascade DB ;
  3. passage de la colonne en NOT NULL.

Sur une base neuve / vidée, l'étape 2 est un no-op.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9648ff99fc55'
down_revision = 'a198cb1d821c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('conversations', sa.Column('product_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f('fk_conversations_product_id_products'),
        'conversations',
        'products',
        ['product_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.execute("DELETE FROM conversations WHERE product_id IS NULL")
    op.alter_column('conversations', 'product_id', existing_type=sa.UUID(), nullable=False)
    op.create_index(op.f('ix_conversations_product_id'), 'conversations', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_conversations_product_id'), table_name='conversations')
    op.drop_constraint(op.f('fk_conversations_product_id_products'), 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'product_id')
