"""add new_issue event type

Revision ID: b7e2f4a1c9d6
Revises: a4f1c2d9e7b3
Create Date: 2026-09-13

Audit (point 4 — multi-sujets dans une même conversation) : une conversation
reste liée à un seul produit, mais peut désormais contenir plusieurs cycles
de diagnostic successifs (plusieurs incidents distincts). Le passage d'un
cycle au suivant est marqué par un nouvel événement `new_issue` (posé par
l'outil `start_new_issue`), qui NE SUPPRIME RIEN : tout l'historique
(recherches, diagnostics, feedbacks, escalades, tickets) reste consultable
tel quel. Seule la lecture "vivante" (récapitulatif LLM, description de
ticket) est scopée au cycle en cours via `events_since_last_new_issue`.

Élargit uniquement la contrainte CHECK sur `event_type` pour autoriser cette
nouvelle valeur — aucune donnée existante n'est modifiée ni supprimée,
migration non destructive et réversible.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'b7e2f4a1c9d6'
down_revision = 'a4f1c2d9e7b3'
branch_labels = None
depends_on = None

_OLD_VALUES = "'search', 'diagnosis', 'feedback', 'escalation', 'ticket'"
_NEW_VALUES = "'search', 'diagnosis', 'feedback', 'escalation', 'ticket', 'new_issue'"


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_conversation_events_event_type_valid"), "conversation_events", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_conversation_events_event_type_valid"),
        "conversation_events",
        f"event_type IN ({_NEW_VALUES})",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_conversation_events_event_type_valid"), "conversation_events", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_conversation_events_event_type_valid"),
        "conversation_events",
        f"event_type IN ({_OLD_VALUES})",
    )
