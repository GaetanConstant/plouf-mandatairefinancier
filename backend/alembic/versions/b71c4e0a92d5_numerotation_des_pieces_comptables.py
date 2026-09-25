"""Numérotation des pièces comptables

Attribue un numéro aux écritures existantes, qui n'en avaient aucun : la colonne
`num_piece` existait depuis le schéma initial mais rien ne l'écrivait, si bien
que la main courante et le livre des comptes affichaient une colonne « N° pièce »
toujours vide.

La numérotation initiale suit l'ordre chronologique — c'est l'ordre du journal,
donc celui dans lequel le mandataire classe ses pièces. Elle est attribuée une
fois : à partir de là, chaque nouvelle écriture prend le rang suivant et aucun
numéro n'est jamais réattribué.

Revision ID: b71c4e0a92d5
Revises: 129c0fb66b13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b71c4e0a92d5'
down_revision: Union[str, Sequence[str], None] = '129c0fb66b13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, colonne de date, préfixe) — cf. backend/pieces.py, même format.
_TABLES = (
    ("depense", "date_facture", "D"),
    ("recette", "date_versement", "R"),
)


def upgrade() -> None:
    op.create_table(
        "compteur_piece",
        sa.Column("prefixe", sa.String(length=4), nullable=False),
        sa.Column("dernier", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("prefixe"),
    )
    bind = op.get_bind()
    for table, colonne_date, prefixe in _TABLES:
        # Les dates manquantes en fin, comme dans le tri de la main courante.
        lignes = bind.execute(sa.text(
            f"SELECT id FROM {table} WHERE num_piece IS NULL OR num_piece = '' "
            f"ORDER BY {colonne_date} IS NULL, {colonne_date}, id"
        )).scalars().all()
        depart = bind.execute(sa.text(
            f"SELECT COUNT(*) FROM {table} WHERE num_piece IS NOT NULL AND num_piece != ''"
        )).scalar_one()
        for rang, ligne_id in enumerate(lignes, start=depart + 1):
            bind.execute(
                sa.text(f"UPDATE {table} SET num_piece = :n WHERE id = :i"),
                {"n": f"{prefixe}{rang:03d}", "i": ligne_id},
            )
        # Le compteur repart du dernier rang attribué : la prochaine écriture
        # prend la suite, aucun numéro déjà classé n'est réutilisé.
        bind.execute(
            sa.text("INSERT INTO compteur_piece (prefixe, dernier) VALUES (:p, :d)"),
            {"p": prefixe, "d": depart + len(lignes)},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for table, _, _ in _TABLES:
        bind.execute(sa.text(f"UPDATE {table} SET num_piece = NULL"))
    op.drop_table("compteur_piece")
