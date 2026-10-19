"""Doublons de lignes bancaires entre deux imports.

L'export « opérations du jour » de La Banque Postale est cumulatif : le
télécharger deux fois dans la journée redonne les premières lignes. Et l'export
d'historique reprend ensuite toutes ces opérations, parfois à la date de
comptabilisation plutôt qu'à celle d'opération. D'où deux règles :

  - la date se compare à quelques jours près ;
  - deux lignes identiques **d'un même import** sont deux opérations réelles
    (deux chèques du même montant le même jour) : un fichier bancaire ne liste
    jamais deux fois la même. Seul un import différent peut faire doublon.

Chaque ligne déjà connue n'absorbe qu'une seule copie par import : si le fichier
porte deux fois une opération que la base n'a qu'une fois, l'une des deux est
nouvelle.

Rien ici ne supprime : on signale, la personne décide.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from sqlalchemy import select

from db.models import ImputationBancaire, ImputationRecette, TransactionBancaire

JOURS_TOLERANCE = 5


def _cle(sens: str, montant: float, libelle: str) -> tuple:
    return (sens, round(montant, 2), " ".join((libelle or "").upper().split())[:255])


def _sens(t: TransactionBancaire) -> str:
    return t.sens.value if hasattr(t.sens, "value") else str(t.sens)


def _proche(a: date, b: date) -> bool:
    return abs((a - b).days) <= JOURS_TOLERANCE


def _decrire(t: TransactionBancaire) -> dict:
    return {
        "id": t.id,
        "date_operation": t.date_operation.strftime("%d/%m/%Y"),
        "releve": t.releve.libelle if t.releve else None,
    }


def marquer_lignes_lues(s, lignes: list[dict]) -> list[dict]:
    """Annote l'aperçu d'import : `deja_present` désigne la ligne déjà en base.

    Les lignes lues forment un seul import ; chacune ne peut donc consommer
    qu'une ligne existante, et chaque ligne existante qu'une ligne lue.
    """
    existantes: dict[tuple, list[TransactionBancaire]] = {}
    for t in s.scalars(select(TransactionBancaire).order_by(TransactionBancaire.id)).all():
        existantes.setdefault(_cle(_sens(t), t.montant, t.libelle), []).append(t)

    prises: set[int] = set()
    for ligne in lignes:
        jour = date.fromisoformat(ligne["date_operation"])
        candidates = [t for t in existantes.get(
            _cle(ligne["sens"], ligne["montant"], ligne["libelle"]), [])
            if t.id not in prises and _proche(t.date_operation, jour)]
        jumelle = min(candidates, key=lambda t: abs((t.date_operation - jour).days), default=None)
        if jumelle is not None:
            prises.add(jumelle.id)
        ligne["deja_present"] = _decrire(jumelle) if jumelle else None
    return lignes


def doublons_en_base(s) -> dict[int, dict]:
    """Lignes déjà enregistrées qui répètent une ligne d'un autre import.

    Renvoie, pour chaque ligne à retirer, la ligne qu'elle répète. Entre deux
    copies, on garde la rapprochée, sinon la plus ancienne : supprimer celle qui
    porte un rapprochement obligerait à le refaire.
    """
    imputees = set(s.scalars(select(ImputationBancaire.transaction_id)).all()) \
        | set(s.scalars(select(ImputationRecette.transaction_id)).all())

    groupes: dict[tuple, list[TransactionBancaire]] = {}
    for t in s.scalars(select(TransactionBancaire)).all():
        groupes.setdefault(_cle(_sens(t), t.montant, t.libelle), []).append(t)

    doublons: dict[int, dict] = {}
    for groupe in groupes.values():
        if len(groupe) < 2:
            continue
        gardees: list[TransactionBancaire] = []
        # (ligne gardée, import) : une ligne gardée n'absorbe qu'une copie par import.
        absorbees: set[tuple[int, int]] = set()
        for t in sorted(groupe, key=lambda t: (t.id not in imputees, t.id)):
            jumelle = _jumelle(t, gardees, absorbees)
            if jumelle is None:
                gardees.append(t)
            else:
                absorbees.add((jumelle.id, t.releve_id))
                doublons[t.id] = _decrire(jumelle)
    return doublons


def _jumelle(t: TransactionBancaire, gardees: Iterable[TransactionBancaire],
             absorbees: set[tuple[int, int]]) -> Optional[TransactionBancaire]:
    candidates = [g for g in gardees
                  if g.releve_id != t.releve_id
                  and (g.id, t.releve_id) not in absorbees
                  and _proche(g.date_operation, t.date_operation)]
    return min(candidates, key=lambda g: abs((g.date_operation - t.date_operation).days),
               default=None)
