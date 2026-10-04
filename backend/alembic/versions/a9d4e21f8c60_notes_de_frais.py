"""Notes de frais

Regroupe les dépenses avancées par une même personne en un document qu'elle
signe et qui justifie son remboursement. Une personne qui avance dix petites
sommes dans le mois attend un seul virement et un seul papier.

L'état de la note ne se stocke pas : elle est remboursée quand toutes ses
dépenses sont rapprochées au relevé. Deux vérités — une case cochée et le
compte — finiraient par diverger.

Revision ID: a9d4e21f8c60
Revises: f1c7a3e92d48
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a9d4e21f8c60'
down_revision: Union[str, Sequence[str], None] = 'f1c7a3e92d48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "note_frais",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("election_id", sa.Integer(), nullable=False),
        sa.Column("personne", sa.String(length=255), nullable=False),
        sa.Column("date_creation", sa.Date(), nullable=True),
        sa.Column("commentaire", sa.Text(), nullable=True),
        sa.Column("justificatif_doc_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["election_id"], ["election.id"]),
        sa.ForeignKeyConstraint(["justificatif_doc_id"], ["document.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("depense", sa.Column("note_frais_id", sa.Integer(), nullable=True))
    op.create_index("ix_depense_note_frais", "depense", ["note_frais_id"])


def downgrade() -> None:
    op.drop_index("ix_depense_note_frais", table_name="depense")
    op.drop_column("depense", "note_frais_id")
    op.drop_table("note_frais")
