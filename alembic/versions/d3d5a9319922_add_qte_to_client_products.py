"""add qte to client_products

Revision ID: d3d5a9319922
Revises: 9648ff99fc55
Create Date: 2026-09-09

Quantité d'un produit affectée à un client. `NOT NULL`, `server_default = 1`
(les lignes existantes prennent 1) + contrainte CHECK `qte >= 1` (une
affectation à 0 n'a pas de sens métier — pour ne plus rien affecter on
supprime la ligne).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3d5a9319922'
down_revision = '9648ff99fc55'
branch_labels = None
depends_on = None


# `naming_convention` d'Alembic préfixe automatiquement en
# "ck_%(table_name)s_%(constraint_name)s" -> ck_client_products_qte_positive
# (identique au modèle : CheckConstraint(..., name="qte_positive")).
_CK = 'qte_positive'


def upgrade() -> None:
    op.add_column(
        'client_products',
        sa.Column('qte', sa.Integer(), nullable=False, server_default='1'),
    )
    op.create_check_constraint(_CK, 'client_products', 'qte >= 1')


def downgrade() -> None:
    # op.f() : nom déjà complet, ne pas re-préfixer via la naming_convention.
    op.drop_constraint(op.f(f'ck_client_products_{_CK}'), 'client_products', type_='check')
    op.drop_column('client_products', 'qte')
