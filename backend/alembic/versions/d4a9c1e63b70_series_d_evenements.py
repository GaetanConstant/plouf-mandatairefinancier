"""Séries d'événements récurrents

Un événement qui se répète — un tractage tous les samedis — devient autant
d'événements que de dates. Chacun est un événement normal : le calendrier, la
frise et le calcul des coûts fonctionnent sans modification, et une dépense se
rattache à l'occurrence précise qui la justifie.

`serie_id` les relie, pour pouvoir les regrouper à l'affichage plus tard sans
avoir à migrer de nouveau.

Revision ID: d4a9c1e63b70
Revises: c38f1a7b4e02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd4a9c1e63b70'
down_revision: Union[str, Sequence[str], None] = 'c38f1a7b4e02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("evenement", sa.Column("serie_id", sa.String(length=36), nullable=True))
    op.create_index("ix_evenement_serie", "evenement", ["serie_id"])


def downgrade() -> None:
    op.drop_index("ix_evenement_serie", table_name="evenement")
    op.drop_column("evenement", "serie_id")
