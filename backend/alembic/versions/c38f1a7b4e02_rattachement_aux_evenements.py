"""Rattachement d'une dépense à un événement

Ajoute le drapeau « hors événement » sur la dépense. Sans lui, impossible de
distinguer une dépense qu'on n'a pas encore rattachée d'une dépense qui n'a
rien à rattacher : le reste à faire ne tomberait jamais à zéro.

Revision ID: c38f1a7b4e02
Revises: b71c4e0a92d5
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c38f1a7b4e02'
down_revision: Union[str, Sequence[str], None] = 'b71c4e0a92d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default : les lignes existantes valent « à rattacher », pas
    # « rien à rattacher ». Une dépense déjà saisie n'a jamais été arbitrée.
    op.add_column("depense", sa.Column("hors_evenement", sa.Boolean(),
                                       nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("depense", "hors_evenement")
