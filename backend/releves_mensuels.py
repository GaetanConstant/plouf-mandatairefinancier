"""Relevés mensuels : le PDF de la banque, pièce justificative de l'enveloppe B.

Distinct des imports (CSV, copier-coller, saisie), qui ne servent qu'à reporter
les lignes du compte pour le rapprochement et la main courante. Un import
n'est pas un relevé : trois exports du jour ne font pas trois relevés.

On attend un PDF par mois de vie du compte, de son ouverture à sa clôture. Un
compte encore ouvert n'exige pas le mois en cours : la banque ne l'a pas émis.
"""

from __future__ import annotations

import os
import re
from datetime import date
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from database import ROLE_MANDATAIRE
from db import enums
from db.helpers import fmt_date, media_type
from db.models import CompteBancaire, Document, Mandataire, TransactionBancaire
from db.session import campaign_session, ensure_campaign_db
import validation

_PERIODE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class PeriodeCompteIn(BaseModel):
    date_ouverture: Optional[str] = None
    date_cloture: Optional[str] = None


class ReleveMensuelIn(BaseModel):
    fichier: str
    periode: str


class DaterIn(BaseModel):
    periode: str


def _verifier_periode(periode: str) -> str:
    if not _PERIODE.match(periode or ""):
        raise HTTPException(status_code=400, detail="Mois attendu au format AAAA-MM.")
    return periode


def _lire_date(valeur: Optional[str]) -> Optional[date]:
    if not valeur:
        return None
    try:
        return date.fromisoformat(valeur)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Date illisible : {valeur}")


def mois_attendus(debut: Optional[date], fin: Optional[date], aujourdhui: date) -> list[str]:
    """Mois dont la banque doit avoir émis un relevé, du plus ancien au plus récent."""
    if debut is None:
        return []
    if fin is None:
        # Compte ouvert : le mois en cours n'a pas encore de relevé.
        fin = (date(aujourdhui.year - 1, 12, 1) if aujourdhui.month == 1
               else date(aujourdhui.year, aujourdhui.month - 1, 1))
    mois = []
    annee, m = debut.year, debut.month
    while (annee, m) <= (fin.year, fin.month):
        mois.append(f"{annee:04d}-{m:02d}")
        annee, m = (annee + 1, 1) if m == 12 else (annee, m + 1)
    return mois


def _doc_dict(d: Document) -> dict:
    return {"id": d.id, "fichier": os.path.basename(d.fichier), "periode": d.periode,
            "media_type": d.media_type}


def etat(campaign_id: str, aujourdhui: Optional[date] = None) -> dict:
    """Mois attendus, PDF déposés pour chacun, et PDF qui n'ont pas encore de mois."""
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        compte = s.scalars(select(CompteBancaire)).first()
        ouverture = compte.date_ouverture if compte else None
        cloture = compte.date_cloture if compte else None
        # Sans date d'ouverture, la première ligne importée donne un point de départ.
        debut = ouverture or s.scalar(select(func.min(TransactionBancaire.date_operation)))
        docs = s.scalars(select(Document)
                         .where(Document.type == enums.TypeDocument.releve_bancaire)
                         .order_by(Document.periode, Document.id)).all()
        attendus = mois_attendus(debut, cloture, aujourdhui or date.today())
        par_mois: dict[str, list[dict]] = {}
        for d in docs:
            if d.periode:
                par_mois.setdefault(d.periode, []).append(_doc_dict(d))
        # Un PDF déposé hors de la période du compte reste visible.
        tous = sorted(set(attendus) | set(par_mois))
        return {
            "date_ouverture": fmt_date(ouverture),
            "date_cloture": fmt_date(cloture),
            "ouverture_deduite": ouverture is None and debut is not None,
            "mois": [{"periode": p, "attendu": p in attendus, "documents": par_mois.get(p, [])}
                     for p in tous],
            "a_dater": [_doc_dict(d) for d in docs if not d.periode],
            "manquants": [p for p in attendus if p not in par_mois],
        }


def deposer(campaign_id: str, payload: ReleveMensuelIn, auteur: str) -> dict:
    periode = _verifier_periode(payload.periode)
    nom = os.path.basename(payload.fichier)
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        piece = Document(type=enums.TypeDocument.releve_bancaire, media_type=media_type(nom),
                         fichier=nom, enveloppe=enums.Enveloppe.B, periode=periode)
        validation.estampiller(piece, auteur, ROLE_MANDATAIRE)
        s.add(piece)
    return etat(campaign_id)


def dater(campaign_id: str, doc_id: int, payload: DaterIn) -> dict:
    periode = _verifier_periode(payload.periode)
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        d = s.get(Document, doc_id)
        if not d or d.type != enums.TypeDocument.releve_bancaire:
            raise HTTPException(status_code=404, detail="Relevé introuvable")
        d.periode = periode
    return etat(campaign_id)


def enregistrer_periode_compte(campaign_id: str, payload: PeriodeCompteIn) -> dict:
    """Dates d'ouverture et de clôture du compte, sans toucher au reste du compte."""
    ouverture, cloture = _lire_date(payload.date_ouverture), _lire_date(payload.date_cloture)
    if ouverture and cloture and cloture < ouverture:
        raise HTTPException(status_code=400, detail="La clôture précède l'ouverture.")
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        compte = s.scalars(select(CompteBancaire)).first()
        if compte is None:
            mandataire = s.scalars(select(Mandataire)).first()
            if mandataire is None:
                raise HTTPException(status_code=400,
                    detail="Renseignez d'abord le mandataire dans Identité : le compte lui est rattaché.")
            compte = CompteBancaire(mandataire_id=mandataire.id)
            s.add(compte)
        compte.date_ouverture = ouverture
        compte.date_cloture = cloture
    return etat(campaign_id)
