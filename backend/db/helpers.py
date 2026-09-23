"""Helpers partagés par la couche service (anti-duplication)."""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import select

from db.models import Election


def election_id(session) -> Optional[int]:
    """Id de l'unique Election de la campagne (None si pas encore créée)."""
    e = session.scalars(select(Election)).first()
    return e.id if e else None


def fmt_date(d) -> Optional[str]:
    """Formate une date en 'YYYY-MM-DD' (None -> None)."""
    if d is None:
        return None
    return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)


def media_type(filename: Optional[str]) -> str:
    """Famille de média d'un fichier joint (image, pdf, autre)."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".heic"):
        return "image"
    if ext == ".pdf":
        return "pdf"
    return "autre"


def valides(requete, modele):
    """Restreint une requête aux objets validés par le mandataire.

    À appliquer sur **tout** calcul qui alimente le compte : plafond,
    trésorerie, conformité, main courante, exports, dossier de dépôt. Ce qu'un
    militant ou l'expert-comptable dépose reste en attente et ne doit pas
    déplacer un chiffre légal avant arbitrage.
    """
    from db import enums

    return requete.where(modele.statut_validation == enums.StatutValidation.valide)
