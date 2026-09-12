"""add unique active ticket per conversation constraint

Revision ID: a4f1c2d9e7b3
Revises: c7a1e9f04b28
Create Date: 2026-09-12

I3 (audit workflow diagnostic/résolution/escalade) : garantie ATOMIQUE, côté
PostgreSQL, qu'une conversation ne peut jamais avoir plus d'un ticket ACTIF
(statut différent de 'closed') simultanément. Sans cette contrainte, deux
requêtes quasi simultanées (double clic, retry réseau côté client) pouvaient
chacune passer la vérification applicative « pas de ticket actif » avant que
l'une des deux ne committe, créant deux tickets pour un même incident — une
vérification en lecture puis écriture (`get_active_ticket_by_conversation`
puis `create_ticket`) n'est jamais atomique à elle seule.

Index unique PARTIEL (PostgreSQL) : ne s'applique qu'aux lignes avec
`status <> 'closed'` — plusieurs tickets déjà `closed` pour une même
conversation restent autorisés (historique), et plusieurs tickets créés
manuellement par le staff (`conversation_id IS NULL`) ne sont jamais concernés
(NULL est toujours distinct de NULL pour une contrainte d'unicité).

Vérifié avant écriture de cette migration : aucune conversation existante
n'a actuellement plus d'un ticket actif (requête de contrôle exécutée sur la
base réelle) — migration NON destructive, réversible.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4f1c2d9e7b3'
down_revision = 'c7a1e9f04b28'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        'ux_tickets_active_per_conversation',
        'tickets',
        ['conversation_id'],
        unique=True,
        postgresql_where=sa.text("status <> 'closed'"),
    )


def downgrade() -> None:
    op.drop_index('ux_tickets_active_per_conversation', table_name='tickets')
