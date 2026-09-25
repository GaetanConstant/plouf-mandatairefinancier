"""Concours en nature — annexe 4 et 4.1 du compte de campagne.

Un concours en nature est un bien ou un service fourni gratuitement à la
campagne : prêt d'un local, mise à disposition d'un véhicule, prestation
bénévole valorisée. Il entre dans le plafond des dépenses sans passer par la
trésorerie, et la commission exige d'en connaître l'origine — candidat,
formation politique ou tiers personne physique — la nature et l'évaluation.

C'est une entité distincte des dépenses : le formulaire CNCCFP en fait sa
propre colonne verticale, et l'annexe 4.1 réclame des informations qu'une
dépense ne porte pas (méthode d'évaluation, fournisseur qualifié).
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from database import ROLE_MANDATAIRE
from db.helpers import election_id as _election_id, media_type
from db.models import ConcoursNature, Document
from db.session import campaign_session, ensure_campaign_db
from db import enums

LIBELLE_ORIGINE = {
    enums.OrigineConcours.candidat: "Candidat",
    enums.OrigineConcours.parti: "Formation politique",
    enums.OrigineConcours.tiers_pp: "Tiers personne physique",
}


class ConcoursIn(BaseModel):
    origine: str
    nature: str
    valeur_estimee: float
    methode_evaluation: Optional[str] = None
    rubrique_imputation: Optional[str] = None
    justificatif_path: Optional[str] = None


def _dict(s, c: ConcoursNature) -> dict:
    doc = s.get(Document, c.justificatif_doc_id) if c.justificatif_doc_id else None
    return {
        "id": c.id,
        "origine": c.origine.value,
        "origine_label": LIBELLE_ORIGINE.get(c.origine, c.origine.value),
        "nature": c.nature,
        "valeur_estimee": c.valeur_estimee,
        "methode_evaluation": c.methode_evaluation,
        "rubrique_imputation": c.rubrique_imputation,
        "justificatif_path": doc.fichier if doc else None,
    }


def list_concours(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        return [_dict(s, c) for c in s.scalars(
            select(ConcoursNature).order_by(ConcoursNature.origine)).all()]


def synthese(campaign_id: str) -> dict:
    """Annexe 4 : les totaux par origine, qui alimentent le formulaire."""
    lignes = list_concours(campaign_id)
    par_origine = {}
    for origine, libelle in LIBELLE_ORIGINE.items():
        montant = sum(l["valeur_estimee"] for l in lignes if l["origine"] == origine.value)
        par_origine[origine.value] = {"libelle": libelle, "montant": round(montant, 2)}
    return {
        "par_origine": par_origine,
        "total": round(sum(l["valeur_estimee"] for l in lignes), 2),
        "nombre": len(lignes),
    }


def create_concours(campaign_id: str, payload: ConcoursIn, auteur: Optional[str] = None,
                    role: str = ROLE_MANDATAIRE) -> dict:
    ensure_campaign_db(campaign_id)
    try:
        origine = enums.OrigineConcours(payload.origine)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Origine inconnue : {payload.origine}")
    if payload.valeur_estimee <= 0:
        raise HTTPException(status_code=400,
                            detail="Un concours en nature doit porter une valeur estimée positive.")

    with campaign_session(campaign_id) as s:
        justificatif_id = None
        if payload.justificatif_path:
            fichier = os.path.basename(payload.justificatif_path)
            doc = Document(type=enums.TypeDocument.autre, media_type=media_type(fichier),
                           fichier=fichier, enveloppe=enums.Enveloppe.B)
            import validation
            validation.estampiller(doc, auteur, role)
            s.add(doc)
            s.flush()
            justificatif_id = doc.id

        c = ConcoursNature(
            election_id=_election_id(s), origine=origine, nature=payload.nature,
            valeur_estimee=payload.valeur_estimee,
            methode_evaluation=payload.methode_evaluation,
            rubrique_imputation=payload.rubrique_imputation,
            justificatif_doc_id=justificatif_id,
        )
        s.add(c)
        s.flush()
        return _dict(s, c)


def update_concours(campaign_id: str, concours_id: int, payload: ConcoursIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        c = s.get(ConcoursNature, concours_id)
        if not c:
            raise HTTPException(status_code=404, detail="Concours introuvable")
        c.origine = enums.OrigineConcours(payload.origine)
        c.nature = payload.nature
        c.valeur_estimee = payload.valeur_estimee
        c.methode_evaluation = payload.methode_evaluation
        c.rubrique_imputation = payload.rubrique_imputation
        return _dict(s, c)


def delete_concours(campaign_id: str, concours_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        c = s.get(ConcoursNature, concours_id)
        if c:
            s.delete(c)
    return {"message": "Concours en nature supprimé."}
