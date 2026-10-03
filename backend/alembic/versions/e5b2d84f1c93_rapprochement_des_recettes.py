"""Rapprochement bancaire des recettes

Le rapprochement ne connaissait que les dépenses : `imputation_bancaire` lie
une ligne de relevé à une dépense, et rien n'existait côté encaissement.

Table dédiée plutôt que `depense_id` rendu nullable : rendre la colonne
nullable imposerait de recréer `imputation_bancaire`, donc de la vider puis
la remplir, sur des rapprochements déjà faits en production. Les deux sens
sont de toute façon asymétriques — un débit solde une dépense, un crédit
alimente une recette.

Revision ID: e5b2d84f1c93
Revises: d4a9c1e63b70
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e5b2d84f1c93'
down_revision: Union[str, Sequence[str], None] = 'd4a9c1e63b70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "imputation_recette",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("recette_id", sa.Integer(), nullable=False),
        sa.Column("montant", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["transaction_bancaire.id"]),
        sa.ForeignKeyConstraint(["recette_id"], ["recette.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_imputation_recette_recette", "imputation_recette", ["recette_id"])


def downgrade() -> None:
    op.drop_index("ix_imputation_recette_recette", table_name="imputation_recette")
    op.drop_table("imputation_recette")
