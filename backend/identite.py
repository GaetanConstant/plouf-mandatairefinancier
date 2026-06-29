"""Module Identité administrative (spec §6.1, socle à remplir en premier).

Gère les entités d'identité d'une campagne, traitées comme des singletons :
Election, Candidat, Mandataire, ExpertComptable, CompteBancaire.

Sauvegarde de l'Election : recalcule les échéances légales (dépôt, clôture) via
le moteur de dates dès que la date du 1er tour est connue.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select

import election_dates
from db.models import Candidat, CompteBancaire, Election, ExpertComptable, Mandataire
from db.session import campaign_session, ensure_campaign_db
from db import enums


# ── Schémas d'entrée (tous champs optionnels : édition progressive) ───────────

class ElectionIn(BaseModel):
    type: Optional[str] = None
    libelle: Optional[str] = None
    circonscription: Optional[str] = None
    population: Optional[int] = None
    nom_liste: Optional[str] = None
    nuance_politique: Optional[str] = None
    date_tour1: Optional[str] = None
    date_tour2: Optional[str] = None
    plafond_depenses: Optional[float] = None
    date_depot_surcharge: Optional[str] = None


class CandidatIn(BaseModel):
    civilite: Optional[str] = None
    nom: Optional[str] = None
    nom_usage: Optional[str] = None
    prenom: Optional[str] = None
    date_naissance: Optional[str] = None
    lieu_naissance: Optional[str] = None
    mandat_parlementaire: Optional[str] = None
    tete_de_liste: Optional[bool] = None
    adresse_postale: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    email: Optional[str] = None
    tel: Optional[str] = None
    adresse_post_campagne: Optional[str] = None
    remplacant_identite: Optional[str] = None


class MandataireIn(BaseModel):
    type: Optional[str] = None  # physique | afe
    civilite: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    date_naissance: Optional[str] = None
    adresse_postale: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    email: Optional[str] = None
    tel: Optional[str] = None
    date_declaration_prefecture: Optional[str] = None
    prefecture: Optional[str] = None
    incompatibilites_verifiees: Optional[bool] = None
    capacite_civile_ok: Optional[bool] = None
    interdiction_bancaire: Optional[bool] = None


class ExpertComptableIn(BaseModel):
    dispense: Optional[bool] = None
    cabinet: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    adresse_postale: Optional[str] = None
    email: Optional[str] = None
    tel: Optional[str] = None
    date_designation: Optional[str] = None
    mission_etendue: Optional[bool] = None


class CompteBancaireIn(BaseModel):
    banque: Optional[str] = None
    libelle: Optional[str] = None
    iban: Optional[str] = None
    date_ouverture: Optional[str] = None
    date_cloture: Optional[str] = None
    droit_au_compte_active: Optional[bool] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _d(s: Optional[str]) -> Optional[date]:
    return date.fromisoformat(s) if s else None


def _fmt(d) -> Optional[str]:
    if d is None:
        return None
    return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)


def _apply(obj, payload: BaseModel, date_fields: set[str], enum_fields: dict | None = None) -> None:
    """Applique les champs fournis (non None) sur l'objet ORM, avec conversions."""
    enum_fields = enum_fields or {}
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if field in date_fields:
            value = _d(value)
        elif field in enum_fields:
            value = enum_fields[field](value)
        setattr(obj, field, value)


def _get_or_create(s, model, **defaults):
    obj = s.scalars(select(model)).first()
    if obj is None:
        obj = model(**defaults)
        s.add(obj)
        s.flush()
    return obj


# ── Lecture globale ──────────────────────────────────────────────────────────

def get_identite(campaign_id: str) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        election = s.scalars(select(Election)).first()
        candidat = s.scalars(select(Candidat)).first()
        mandataire = s.scalars(select(Mandataire)).first()
        expert = s.scalars(select(ExpertComptable)).first()
        compte = s.scalars(select(CompteBancaire)).first()
        return {
            "election": _election_dict(election),
            "candidat": _candidat_dict(candidat),
            "mandataire": _mandataire_dict(mandataire),
            "expert_comptable": _expert_dict(expert),
            "compte_bancaire": _compte_dict(compte),
        }


def _election_dict(e: Optional[Election]) -> Optional[dict]:
    if not e:
        return None
    return {
        "type": e.type.value if e.type else None,
        "libelle": e.libelle,
        "circonscription": e.circonscription,
        "population": e.population,
        "nom_liste": e.nom_liste,
        "nuance_politique": e.nuance_politique,
        "date_tour1": _fmt(e.date_tour1),
        "date_tour2": _fmt(e.date_tour2),
        "plafond_depenses": e.plafond_depenses,
        "date_limite_depot": _fmt(e.date_limite_depot),
        "date_cloture_compte": _fmt(e.date_cloture_compte),
        "date_depot_surcharge": _fmt(e.date_depot_surcharge),
    }


def _candidat_dict(c: Optional[Candidat]) -> Optional[dict]:
    if not c:
        return None
    return {k: getattr(c, k) for k in (
        "civilite", "nom", "nom_usage", "prenom", "tete_de_liste",
        "lieu_naissance", "mandat_parlementaire",
        "adresse_postale", "code_postal", "ville", "email", "tel",
        "adresse_post_campagne", "remplacant_identite")} | {"date_naissance": _fmt(c.date_naissance)}


def _mandataire_dict(m: Optional[Mandataire]) -> Optional[dict]:
    if not m:
        return None
    return {k: getattr(m, k) for k in (
        "civilite", "nom", "prenom", "adresse_postale", "code_postal", "ville",
        "email", "tel", "prefecture", "incompatibilites_verifiees",
        "capacite_civile_ok", "interdiction_bancaire")} | {
        "type": m.type.value if m.type else None,
        "date_naissance": _fmt(m.date_naissance),
        "date_declaration_prefecture": _fmt(m.date_declaration_prefecture),
    }


def _expert_dict(x: Optional[ExpertComptable]) -> Optional[dict]:
    if not x:
        return None
    return {k: getattr(x, k) for k in (
        "dispense", "cabinet", "nom", "prenom", "adresse_postale", "email",
        "tel", "mission_etendue")} | {"date_designation": _fmt(x.date_designation)}


def _compte_dict(c: Optional[CompteBancaire]) -> Optional[dict]:
    if not c:
        return None
    return {k: getattr(c, k) for k in ("banque", "libelle", "iban", "droit_au_compte_active")} | {
        "date_ouverture": _fmt(c.date_ouverture),
        "date_cloture": _fmt(c.date_cloture),
    }


# ── Sauvegardes (upsert singleton) ───────────────────────────────────────────

def save_election(campaign_id: str, payload: ElectionIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        e = _get_or_create(s, Election, type=enums.TypeElection.autre, libelle="Campagne")
        _apply(e, payload, {"date_tour1", "date_tour2", "date_depot_surcharge"},
               {"type": enums.TypeElection})
        # Recalcule les échéances dès que le 1er tour est connu.
        if e.date_tour1:
            jalons = election_dates.calculer_jalons(e.date_tour1, e.date_depot_surcharge)
            e.date_limite_depot = jalons.date_limite_depot
            e.date_cloture_compte = jalons.date_cloture_compte
    return get_identite(campaign_id)


def save_candidat(campaign_id: str, payload: CandidatIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        c = _get_or_create(s, Candidat, election_id=_election_id(s), nom="", prenom="")
        _apply(c, payload, {"date_naissance"})
    return get_identite(campaign_id)


def save_mandataire(campaign_id: str, payload: MandataireIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        m = _get_or_create(s, Mandataire, election_id=_election_id(s), type=enums.TypeMandataire.physique)
        _apply(m, payload, {"date_naissance", "date_declaration_prefecture"},
               {"type": enums.TypeMandataire})
    return get_identite(campaign_id)


def save_expert(campaign_id: str, payload: ExpertComptableIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        x = _get_or_create(s, ExpertComptable, election_id=_election_id(s))
        _apply(x, payload, {"date_designation"})
    return get_identite(campaign_id)


def save_compte(campaign_id: str, payload: CompteBancaireIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        mandataire = s.scalars(select(Mandataire)).first()
        mandataire_id = mandataire.id if mandataire else None
        c = s.scalars(select(CompteBancaire)).first()
        if c is None:
            c = CompteBancaire(mandataire_id=mandataire_id)
            s.add(c)
            s.flush()
        elif mandataire_id and not c.mandataire_id:
            c.mandataire_id = mandataire_id
        _apply(c, payload, {"date_ouverture", "date_cloture"})
    return get_identite(campaign_id)


def _election_id(s) -> Optional[int]:
    e = s.scalars(select(Election)).first()
    return e.id if e else None
