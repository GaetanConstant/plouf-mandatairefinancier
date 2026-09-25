"""Dévolution de l'excédent du compte (articles L. 52-5 et L. 52-6).

Un compte excédentaire ne laisse pas le solde au candidat. La règle dépend de
l'origine de l'excédent :

  - s'il provient de l'apport personnel du candidat, il est déduit du
    remboursement forfaitaire et **aucune dévolution n'est due** ;
  - s'il provient de financements extérieurs — dons de personnes physiques ou
    apports de partis — il doit être dévolu.

La commission arrête le montant y compris pour les comptes rejetés ou déposés
hors délai. À défaut de décision, l'actif net va au fonds pour le développement
de la vie associative.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from db.helpers import election_id as _election_id, fmt_date as _fmt, valides as _valides
from db.models import Depense, Devolution, Recette
from db.session import campaign_session, ensure_campaign_db
from db import enums

# Recettes qui constituent un financement extérieur au candidat : c'est leur
# présence dans l'excédent qui déclenche la dévolution.
CATEGORIES_EXTERIEURES = (
    enums.CategorieRecette.don,
    enums.CategorieRecette.contribution_parti,
)

LIBELLE_BENEFICIAIRE = {
    enums.BeneficiaireDevolution.parti: "Mandataire d'une formation politique",
    enums.BeneficiaireDevolution.association: "Association d'intérêt général",
    enums.BeneficiaireDevolution.fonds_vie_associative:
        "Fonds pour le développement de la vie associative",
}


class DevolutionIn(BaseModel):
    beneficiaire_type: str
    beneficiaire_nom: Optional[str] = None
    montant: float
    date_decision: Optional[str] = None
    commentaire: Optional[str] = None


def _total(s, modele, colonne, *filtres) -> float:
    requete = _valides(select(func.coalesce(func.sum(colonne), 0.0)), modele)
    for f in filtres:
        requete = requete.where(f)
    return s.scalar(requete) or 0.0


def etat(campaign_id: str) -> dict:
    """Excédent du compte, son origine, et ce qu'il implique."""
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        recettes = _total(s, Recette, Recette.montant)
        exterieures = _total(s, Recette, Recette.montant,
                             Recette.categorie.in_(CATEGORIES_EXTERIEURES))
        depenses = _total(s, Depense, Depense.montant_ttc)
        enregistree = s.scalars(select(Devolution)).first()
        deja = _devolution_dict(enregistree) if enregistree else None

    excedent = round(recettes - depenses, 2)
    apport_personnel = round(recettes - exterieures, 2)

    # L'excédent est réputé provenir d'abord de l'apport personnel : ce n'est
    # qu'au-delà qu'il mobilise des financements extérieurs, donc qu'il est dû.
    part_exterieure = round(max(0.0, excedent - apport_personnel), 2) if excedent > 0 else 0.0

    return {
        "total_recettes": round(recettes, 2),
        "total_depenses": round(depenses, 2),
        "excedent": excedent,
        "apport_personnel": apport_personnel,
        "financements_exterieurs": round(exterieures, 2),
        "montant_devolution": part_exterieure,
        "devolution_due": part_exterieure > 0,
        "motif": _motif(excedent, part_exterieure),
        "devolution": deja,
    }


def _motif(excedent: float, part_exterieure: float) -> str:
    if excedent <= 0:
        return "Le compte n'est pas excédentaire : aucune dévolution."
    if part_exterieure <= 0:
        return ("L'excédent provient de l'apport personnel du candidat : il sera déduit "
                "du remboursement forfaitaire, sans dévolution.")
    return (f"{part_exterieure:.2f} € proviennent de financements extérieurs "
            "(dons ou apports de partis) et doivent être dévolus.")


def _devolution_dict(d: Devolution) -> dict:
    return {
        "id": d.id,
        "beneficiaire_type": d.beneficiaire_type.value,
        "beneficiaire_label": LIBELLE_BENEFICIAIRE.get(d.beneficiaire_type, ""),
        "beneficiaire_nom": d.beneficiaire_nom,
        "montant": d.montant,
        "date_decision": _fmt(d.date_decision),
        "commentaire": d.commentaire,
    }


def enregistrer(campaign_id: str, payload: DevolutionIn) -> dict:
    """Consigne la décision de dévolution. Une seule par compte."""
    ensure_campaign_db(campaign_id)
    try:
        beneficiaire = enums.BeneficiaireDevolution(payload.beneficiaire_type)
    except ValueError:
        raise HTTPException(status_code=400,
                            detail=f"Bénéficiaire inconnu : {payload.beneficiaire_type}")
    if payload.montant <= 0:
        raise HTTPException(status_code=400, detail="Le montant dévolu doit être positif.")
    if (beneficiaire != enums.BeneficiaireDevolution.fonds_vie_associative
            and not (payload.beneficiaire_nom or "").strip()):
        raise HTTPException(status_code=400,
                            detail="Nommez le bénéficiaire de la dévolution.")

    with campaign_session(campaign_id) as s:
        d = s.scalars(select(Devolution)).first()
        if d is None:
            d = Devolution(election_id=_election_id(s), beneficiaire_type=beneficiaire,
                           montant=payload.montant)
            s.add(d)
        d.beneficiaire_type = beneficiaire
        d.beneficiaire_nom = payload.beneficiaire_nom
        d.montant = payload.montant
        d.date_decision = date.fromisoformat(payload.date_decision) if payload.date_decision else None
        d.commentaire = payload.commentaire
        s.flush()
        return _devolution_dict(d)


def supprimer(campaign_id: str) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        d = s.scalars(select(Devolution)).first()
        if d:
            s.delete(d)
    return {"message": "Décision de dévolution retirée."}
