"""Annexes CNCCFP : colistiers (liste), équipe de campagne (Annexe 7),
emprunts (Annexes 3.2 / 3.3 / 3.4).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from db.models import Colistier, Election, Emprunt, MembreEquipe
from db.session import campaign_session, ensure_campaign_db
from db.helpers import election_id as _election_id, fmt_date as _fmt
from db import enums


def _d(s: Optional[str]) -> Optional[date]:
    return date.fromisoformat(s) if s else None






# ── Colistiers ───────────────────────────────────────────────────────────────

class ColistierIn(BaseModel):
    civilite: Optional[str] = None
    prenom: Optional[str] = None
    nom: str
    mandat_parlementaire: Optional[str] = None
    present_tour1: bool = True
    present_tour2: bool = False
    ordre: Optional[int] = None


def list_colistiers(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        rows = s.scalars(select(Colistier).order_by(Colistier.ordre, Colistier.nom)).all()
        return [{"id": c.id, "civilite": c.civilite, "prenom": c.prenom, "nom": c.nom,
                 "mandat_parlementaire": c.mandat_parlementaire,
                 "present_tour1": c.present_tour1, "present_tour2": c.present_tour2,
                 "ordre": c.ordre} for c in rows]


def create_colistier(campaign_id: str, payload: ColistierIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        c = Colistier(election_id=_election_id(s), **payload.model_dump())
        s.add(c)
        s.flush()
        return {"id": c.id, "message": "Colistier ajouté"}


def delete_colistier(campaign_id: str, colistier_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        c = s.get(Colistier, colistier_id)
        if c:
            s.delete(c)
    return {"message": "Colistier supprimé"}


# ── Équipe de campagne ───────────────────────────────────────────────────────

class MembreEquipeIn(BaseModel):
    prenom: Optional[str] = None
    nom: str
    fonction: Optional[str] = None


def list_equipe(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        rows = s.scalars(select(MembreEquipe).order_by(MembreEquipe.nom)).all()
        return [{"id": m.id, "prenom": m.prenom, "nom": m.nom, "fonction": m.fonction} for m in rows]


def create_membre(campaign_id: str, payload: MembreEquipeIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        m = MembreEquipe(election_id=_election_id(s), **payload.model_dump())
        s.add(m)
        s.flush()
        return {"id": m.id, "message": "Membre ajouté"}


def delete_membre(campaign_id: str, membre_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        m = s.get(MembreEquipe, membre_id)
        if m:
            s.delete(m)
    return {"message": "Membre supprimé"}


# ── Emprunts ─────────────────────────────────────────────────────────────────

class EmpruntIn(BaseModel):
    type: str  # banque | parti | personne_physique
    preteur_nom: Optional[str] = None
    preteur_civilite: Optional[str] = None
    preteur_prenom: Optional[str] = None
    preteur_pays: Optional[str] = None
    date_contrat: Optional[str] = None
    duree_mois: Optional[int] = None
    date_fin: Optional[str] = None
    taux: Optional[float] = None
    montant: float


def list_emprunts(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        rows = s.scalars(select(Emprunt).order_by(Emprunt.date_contrat)).all()
        return [{"id": e.id, "type": e.type.value if e.type else None,
                 "preteur_nom": e.preteur_nom, "preteur_civilite": e.preteur_civilite,
                 "preteur_prenom": e.preteur_prenom, "preteur_pays": e.preteur_pays,
                 "date_contrat": _fmt(e.date_contrat), "duree_mois": e.duree_mois,
                 "date_fin": _fmt(e.date_fin), "taux": e.taux, "montant": e.montant}
                for e in rows]


def create_emprunt(campaign_id: str, payload: EmpruntIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        e = Emprunt(
            election_id=_election_id(s),
            type=enums.TypeEmprunt(payload.type),
            preteur_nom=payload.preteur_nom,
            preteur_civilite=payload.preteur_civilite,
            preteur_prenom=payload.preteur_prenom,
            preteur_pays=payload.preteur_pays,
            date_contrat=_d(payload.date_contrat),
            duree_mois=payload.duree_mois,
            date_fin=_d(payload.date_fin),
            taux=payload.taux,
            montant=payload.montant,
        )
        s.add(e)
        s.flush()
        return {"id": e.id, "message": "Emprunt ajouté"}


def delete_emprunt(campaign_id: str, emprunt_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        e = s.get(Emprunt, emprunt_id)
        if e:
            s.delete(e)
    return {"message": "Emprunt supprimé"}
