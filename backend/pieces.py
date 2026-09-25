"""Numérotation des pièces comptables (annexe 8, bordereau de dépôt).

Chaque écriture porte un numéro définitif — `D001` pour une dépense, `R001`
pour une recette — repris à l'identique dans la main courante, le livre des
comptes et le nom du fichier versé à l'enveloppe. C'est ce qui permet à la
commission de passer d'une ligne du journal à la pièce correspondante sans la
chercher.

Le numéro est attribué à la création et n'est **jamais** recalculé. Renuméroter
après coup ferait mentir tous les justificatifs déjà imprimés, sur lesquels le
numéro est porté à la main.
"""

from __future__ import annotations

import re

from sqlalchemy import select

from db.models import CompteurPiece, Depense, Recette

PREFIXE_DEPENSE = "D"
PREFIXE_RECETTE = "R"
LARGEUR = 3

_PREFIXES = {Depense: PREFIXE_DEPENSE, Recette: PREFIXE_RECETTE}

_FORMAT = re.compile(r"^[A-Z](\d+)$")


def prefixe(modele) -> str:
    try:
        return _PREFIXES[modele]
    except KeyError:
        raise ValueError(f"Aucun préfixe de pièce pour {modele!r}") from None


def formater(rang: int, modele) -> str:
    return f"{prefixe(modele)}{rang:0{LARGEUR}d}"


def rang(numero: str | None) -> int:
    """Rang numérique d'un numéro de pièce, 0 si le format est inattendu."""
    correspondance = _FORMAT.match((numero or "").strip().upper())
    return int(correspondance.group(1)) if correspondance else 0


def prochain_numero(s, modele) -> str:
    """Numéro suivant pour ce modèle, lu et incrémenté sur le compteur persistant.

    Le compteur, et non le plus grand numéro en base : supprimer une écriture
    laisserait un trou que `max()` comblerait, et la pièce suivante reprendrait
    un numéro déjà écrit sur un justificatif classé.
    """
    p = prefixe(modele)
    compteur = s.get(CompteurPiece, p)
    if compteur is None:
        # Première pièce, ou base antérieure au compteur : on repart du plus
        # grand rang déjà attribué pour ne pas réécrire l'existant.
        existants = s.scalars(select(modele.num_piece).where(modele.num_piece.is_not(None))).all()
        compteur = CompteurPiece(prefixe=p, dernier=max((rang(n) for n in existants), default=0))
        s.add(compteur)
    compteur.dernier += 1
    s.flush()
    return formater(compteur.dernier, modele)


def attribuer(s, objet) -> str:
    """Attribue son numéro à une écriture qui n'en a pas encore."""
    if not objet.num_piece:
        objet.num_piece = prochain_numero(s, type(objet))
    return objet.num_piece
