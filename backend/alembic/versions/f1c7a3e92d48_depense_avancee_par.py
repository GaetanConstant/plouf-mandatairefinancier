"""Dépense avancée par une personne

Un colleur qui paie 40 € d'essence crée deux faits : une dépense de campagne
— dont le fournisseur est la station-service — et une dette envers lui. Faute
de pouvoir noter qui a avancé l'argent, il fallait inscrire la personne comme
fournisseur, ce qui fausse la nature de la dépense et le relevé des
fournisseurs.

Revision ID: f1c7a3e92d48
Revises: e5b2d84f1c93
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f1c7a3e92d48'
down_revision: Union[str, Sequence[str], None] = 'e5b2d84f1c93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("depense", sa.Column("avance_par", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("depense", "avance_par")
