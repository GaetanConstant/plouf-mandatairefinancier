"""Relevés mensuels : le PDF de la banque, à part des imports

Le relevé PDF est la pièce justificative de l'enveloppe B ; le CSV ne sert qu'à
alimenter les lignes du compte. Un import n'est pas un relevé : trois exports
du jour ne font pas trois relevés. Le PDF porte donc le mois qu'il couvre.

Les CSV versés jusqu'ici comme pièces « relevé bancaire » quittent le dossier
de dépôt. Leur fichier reste sur le disque, attaché à son import.

Revision ID: b7e2c4f19a30
Revises: a9d4e21f8c60
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b7e2c4f19a30'
down_revision: Union[str, Sequence[str], None] = 'a9d4e21f8c60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document", sa.Column("periode", sa.String(length=7), nullable=True))

    bind = op.get_bind()
    csv_ids = [r[0] for r in bind.execute(sa.text(
        "SELECT id FROM document WHERE type = 'releve_bancaire' AND lower(fichier) LIKE '%.csv'"))]
    if not csv_ids:
        return
    # Aucune pièce ne doit rester pointée par une clé devenue orpheline.
    inspecteur = sa.inspect(bind)
    marqueurs = ", ".join(f":id{i}" for i in range(len(csv_ids)))
    valeurs = {f"id{i}": v for i, v in enumerate(csv_ids)}
    for table in inspecteur.get_table_names():
        for fk in inspecteur.get_foreign_keys(table):
            if fk["referred_table"] == "document":
                for colonne in fk["constrained_columns"]:
                    bind.execute(sa.text(
                        f'UPDATE "{table}" SET "{colonne}" = NULL WHERE "{colonne}" IN ({marqueurs})'),
                        valeurs)
    bind.execute(sa.text(f"DELETE FROM document WHERE id IN ({marqueurs})"), valeurs)


def downgrade() -> None:
    # Les pièces CSV retirées ne sont pas recréées : elles n'avaient pas leur
    # place dans le dossier.
    # DROP COLUMN natif (SQLite ≥ 3.35) : une recréation de table par batch,
    # clés étrangères actives, viderait en cascade les tables qui pointent ici.
    op.execute('ALTER TABLE document DROP COLUMN periode')
