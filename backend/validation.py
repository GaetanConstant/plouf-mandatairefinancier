"""Cycle de validation des objets soumis au mandataire.

L'équipe de campagne et l'expert-comptable peuvent alimenter le compte, mais
rien de ce qu'ils déposent n'y entre avant arbitrage du mandataire : un objet
`propose` est invisible du plafond, de la trésorerie, des exports et du dossier
de dépôt (voir `db.helpers.valides`).

Un refus ne supprime rien. L'objet revient à son auteur avec son motif, qui
peut corriger et resoumettre — sans quoi une erreur de saisie effacerait une
pièce comptable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from database import ROLE_MANDATAIRE
from db.models import DemandePiece, Depense, Document, Evenement, Recette
from db.session import campaign_session, ensure_campaign_db
from db import enums

# Types d'objets soumis à validation, et comment les décrire dans la file.
ENTITES = {
    "depense": (Depense, "Dépense"),
    "recette": (Recette, "Recette"),
    "evenement": (Evenement, "Événement"),
    "document": (Document, "Pièce"),
}


class ArbitrageIn(BaseModel):
    motif: Optional[str] = None


class DemandePieceIn(BaseModel):
    depense_id: Optional[int] = None
    message: str


class ReponseDemandeIn(BaseModel):
    reponse: str


def statut_initial(role: str) -> enums.StatutValidation:
    """Ce que devient un objet à sa création, selon qui le crée."""
    return (enums.StatutValidation.valide if role == ROLE_MANDATAIRE
            else enums.StatutValidation.propose)


def estampiller(objet, auteur: Optional[str], role: str) -> None:
    """Pose l'auteur et le statut d'entrée sur un objet qui vient d'être créé."""
    objet.cree_par = auteur
    objet.cree_le = datetime.now()
    statut = statut_initial(role)
    objet.statut_validation = statut
    if statut == enums.StatutValidation.valide:
        objet.valide_par = auteur
        objet.valide_le = datetime.now()


def _libelle(entite: str, objet) -> str:
    if entite == "depense":
        return f"{objet.nature or 'Dépense'} — {objet.montant_ttc or 0:.2f} €"
    if entite == "recette":
        return f"{objet.montant or 0:.2f} €"
    if entite == "evenement":
        return objet.titre or "Événement"
    return objet.fichier or "Pièce"


def _resume(entite: str, objet) -> dict:
    return {
        "entite": entite,
        "type_label": ENTITES[entite][1],
        "id": objet.id,
        "libelle": _libelle(entite, objet),
        "statut": objet.statut_validation.value,
        "cree_par": objet.cree_par,
        "cree_le": objet.cree_le.isoformat() if objet.cree_le else None,
        "motif_refus": objet.motif_refus,
    }


def _lister(campaign_id: str, statuts: tuple, auteur: Optional[str] = None) -> list[dict]:
    ensure_campaign_db(campaign_id)
    lignes: list[dict] = []
    with campaign_session(campaign_id) as s:
        for entite, (modele, _) in ENTITES.items():
            requete = select(modele).where(modele.statut_validation.in_(statuts))
            if auteur is not None:
                requete = requete.where(modele.cree_par == auteur)
            lignes += [_resume(entite, o) for o in s.scalars(requete).all()]
    lignes.sort(key=lambda l: l["cree_le"] or "", reverse=True)
    return lignes


def file_attente(campaign_id: str) -> dict:
    """Ce qui attend l'arbitrage du mandataire."""
    en_attente = _lister(campaign_id, (enums.StatutValidation.propose,))
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        demandes = s.scalars(select(DemandePiece).where(
            DemandePiece.statut == enums.StatutDemandePiece.ouverte)).all()
        nb_demandes = len(demandes)
    return {
        "elements": en_attente,
        "nb_elements": len(en_attente),
        "nb_demandes_pieces": nb_demandes,
        "total": len(en_attente) + nb_demandes,
    }


def mes_soumissions(campaign_id: str, username: str) -> list[dict]:
    """Ce qu'un contributeur a déposé, et où ça en est."""
    return _lister(campaign_id, tuple(enums.StatutValidation), auteur=username)


def _objet(s, entite: str, objet_id: int):
    if entite not in ENTITES:
        raise HTTPException(status_code=400, detail=f"Type d'objet inconnu : {entite}")
    objet = s.get(ENTITES[entite][0], objet_id)
    if not objet:
        raise HTTPException(status_code=404, detail=f"{ENTITES[entite][1]} introuvable")
    return objet


def valider(campaign_id: str, entite: str, objet_id: int, mandataire: str) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        objet = _objet(s, entite, objet_id)
        objet.statut_validation = enums.StatutValidation.valide
        objet.valide_par = mandataire
        objet.valide_le = datetime.now()
        objet.motif_refus = None
    return {"message": f"{ENTITES[entite][1]} validée et intégrée au compte."}


def refuser(campaign_id: str, entite: str, objet_id: int, mandataire: str,
            motif: Optional[str]) -> dict:
    """Refuse sans supprimer : l'auteur garde son objet et le motif."""
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        objet = _objet(s, entite, objet_id)
        objet.statut_validation = enums.StatutValidation.refuse
        objet.valide_par = mandataire
        objet.valide_le = datetime.now()
        objet.motif_refus = motif
    return {"message": f"{ENTITES[entite][1]} refusée. Son auteur peut la corriger."}


def resoumettre(campaign_id: str, entite: str, objet_id: int, auteur: str) -> dict:
    """Remet en attente un objet refusé, après correction par son auteur."""
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        objet = _objet(s, entite, objet_id)
        if objet.cree_par != auteur:
            raise HTTPException(status_code=403, detail="Cet objet n'est pas le vôtre.")
        if objet.statut_validation != enums.StatutValidation.refuse:
            raise HTTPException(status_code=400, detail="Seul un objet refusé se resoumet.")
        objet.statut_validation = enums.StatutValidation.propose
        objet.motif_refus = None
    return {"message": "Soumis à nouveau au mandataire."}


# ── Demandes de pièces (expert-comptable) ────────────────────────────────────

def _demande_dict(d: DemandePiece) -> dict:
    return {
        "id": d.id,
        "depense_id": d.depense_id,
        "message": d.message,
        "statut": d.statut.value,
        "demande_par": d.demande_par,
        "demande_le": d.demande_le.isoformat() if d.demande_le else None,
        "reponse": d.reponse,
        "repondu_par": d.repondu_par,
        "repondu_le": d.repondu_le.isoformat() if d.repondu_le else None,
    }


def list_demandes(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        demandes = s.scalars(select(DemandePiece).order_by(DemandePiece.demande_le.desc())).all()
        return [_demande_dict(d) for d in demandes]


def create_demande(campaign_id: str, payload: DemandePieceIn, auteur: str) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        if payload.depense_id is not None and not s.get(Depense, payload.depense_id):
            raise HTTPException(status_code=404, detail="Dépense introuvable")
        d = DemandePiece(depense_id=payload.depense_id, message=payload.message,
                         demande_par=auteur, demande_le=datetime.now())
        s.add(d)
        s.flush()
        return _demande_dict(d)


def repondre_demande(campaign_id: str, demande_id: int, payload: ReponseDemandeIn,
                     auteur: str) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        d = s.get(DemandePiece, demande_id)
        if not d:
            raise HTTPException(status_code=404, detail="Demande introuvable")
        d.reponse = payload.reponse
        d.repondu_par = auteur
        d.repondu_le = datetime.now()
        d.statut = enums.StatutDemandePiece.repondue
        return _demande_dict(d)


def clore_demande(campaign_id: str, demande_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        d = s.get(DemandePiece, demande_id)
        if not d:
            raise HTTPException(status_code=404, detail="Demande introuvable")
        d.statut = enums.StatutDemandePiece.close
        return _demande_dict(d)
