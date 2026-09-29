"""Événements de campagne + liaison n-n aux dépenses (spec §7).

Un événement regroupe des dépenses via une table de liaison portant une
quote-part (%). Le coût d'un événement = Σ (montant dépense × quote-part).

⚠️ Anti-double-comptage : la source de vérité financière reste la table Depense.
Le coût par événement est une métrique de pilotage, calculée à la volée, jamais
réinjectée dans les totaux globaux.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from db.models import Depense, Document, Evenement, EvenementDepense
from db.session import campaign_session, ensure_campaign_db
from db.helpers import election_id as _election_id, fmt_date as _fmt, media_type, valides as _valides
from db import enums
from database import ROLE_MANDATAIRE
import validation


class EvenementIn(BaseModel):
    titre: Optional[str] = None
    type: Optional[str] = None
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    lieu: Optional[str] = None
    description: Optional[str] = None


class LiaisonIn(BaseModel):
    depense_id: int
    quote_part: Optional[float] = None  # % ; None = 100 %


class LiaisonEvenementIn(BaseModel):
    """Rattachement vu depuis la dépense : l'événement, et la part qui lui revient."""
    evenement_id: int
    quote_part: Optional[float] = None  # % ; None = 100 %


QUOTE_PART_TOTALE = 100.0


def part(quote_part: Optional[float]) -> float:
    """Quote-part effective : absente vaut la totalité de la dépense."""
    return quote_part if quote_part is not None else QUOTE_PART_TOTALE


def appliquer_liaisons(s, depense_id: int, liaisons: list[LiaisonEvenementIn]) -> None:
    """Remplace les rattachements d'une dépense par la liste fournie.

    Vu depuis la dépense, contrairement à `link_depense` qui ajoute un lien vu
    depuis l'événement. La liste fait foi : un événement absent est détaché.
    La règle Σ quote-parts ≤ 100 % reste la même — c'est le garde-fou contre le
    double comptage d'une même facture sur deux événements.
    """
    vus: set[int] = set()
    total = 0.0
    for liaison in liaisons:
        if liaison.evenement_id in vus:
            raise HTTPException(status_code=400,
                detail="Le même événement est rattaché deux fois à cette dépense.")
        vus.add(liaison.evenement_id)
        if not s.get(Evenement, liaison.evenement_id):
            raise HTTPException(status_code=404, detail="Événement introuvable")
        if liaison.quote_part is not None and not (0 < liaison.quote_part <= QUOTE_PART_TOTALE):
            raise HTTPException(status_code=400,
                detail="Une quote-part doit être comprise entre 0 et 100 %.")
        total += part(liaison.quote_part)
    if total > QUOTE_PART_TOTALE:
        raise HTTPException(status_code=400,
            detail=f"Quote-part totale de cette dépense : {total:.0f} % (maximum 100 %).")

    existants = {l.evenement_id: l for l in s.scalars(
        select(EvenementDepense).where(EvenementDepense.depense_id == depense_id)).all()}
    for liaison in liaisons:
        lien = existants.pop(liaison.evenement_id, None)
        if lien:
            lien.quote_part = liaison.quote_part
        else:
            s.add(EvenementDepense(evenement_id=liaison.evenement_id,
                                   depense_id=depense_id, quote_part=liaison.quote_part))
    for orphelin in existants.values():
        s.delete(orphelin)


def liaisons_de_depense(s, depense_id: int) -> list[dict]:
    """Événements rattachés à une dépense, pour préremplir son formulaire."""
    liens = s.scalars(select(EvenementDepense)
                      .where(EvenementDepense.depense_id == depense_id)).all()
    titres = {e.id: e.titre for e in s.scalars(select(Evenement)).all()}
    return [{"evenement_id": l.evenement_id, "titre": titres.get(l.evenement_id),
             "quote_part": l.quote_part} for l in liens]


class DocumentEvenementIn(BaseModel):
    """Pièce rattachée à un événement : photo prise sur place, facture, contrat.

    `fichier` désigne un fichier déjà téléversé dans `uploads`. `doc_id` rattache
    au contraire une pièce déjà enregistrée (la facture d'une dépense, par
    exemple), sans la dupliquer.
    """
    doc_id: Optional[int] = None
    fichier: Optional[str] = None
    type: str = "photo"


def _d(s: Optional[str]) -> Optional[date]:
    return date.fromisoformat(s) if s else None






def depenses_liees(s, evenement_id: int) -> list[tuple]:
    """Couples (lien, dépense) rattachés à l'événement, dépenses validées seules.

    Le filtre `valides` compte : une dépense déposée par l'équipe ou l'expert
    reste en attente d'arbitrage, et ne doit pas gonfler le coût affiché d'un
    événement avant que le mandataire l'ait acceptée.
    """
    liens = s.scalars(select(EvenementDepense)
                      .where(EvenementDepense.evenement_id == evenement_id)).all()
    if not liens:
        return []
    depenses = {d.id: d for d in s.scalars(
        _valides(select(Depense), Depense)
        .where(Depense.id.in_([l.depense_id for l in liens]))).all()}
    return [(l, depenses[l.depense_id]) for l in liens if l.depense_id in depenses]


def cout_affecte(lien, depense) -> float:
    return (depense.montant_ttc or 0.0) * part(lien.quote_part) / QUOTE_PART_TOTALE


def _cout(s, evenement_id: int) -> float:
    """Σ (montant dépense × quote-part) des dépenses validées de l'événement."""
    return sum(cout_affecte(l, d) for l, d in depenses_liees(s, evenement_id))


def _evenement_dict(s, e: Evenement) -> dict:
    liees = depenses_liees(s, e.id)
    return {
        "id": e.id,
        "titre": e.titre,
        "type": e.type.value if e.type else None,
        "date_debut": _fmt(e.date_debut),
        "date_fin": _fmt(e.date_fin),
        "lieu": e.lieu,
        "description": e.description,
        "nb_depenses": len(liees),
        "cout": sum(cout_affecte(l, d) for l, d in liees),
    }


def list_evenements(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        evs = s.scalars(_valides(select(Evenement), Evenement).order_by(Evenement.date_debut)).all()
        return [_evenement_dict(s, e) for e in evs]


def create_evenement(campaign_id: str, payload: EvenementIn, auteur: str | None = None,
                     role: str = ROLE_MANDATAIRE) -> dict:
    ensure_campaign_db(campaign_id)
    if not payload.titre or not payload.date_debut:
        raise HTTPException(status_code=400, detail="Titre et date de début requis.")
    with campaign_session(campaign_id) as s:
        e = Evenement(
            election_id=_election_id(s),
            titre=payload.titre,
            type=enums.TypeEvenement(payload.type) if payload.type else enums.TypeEvenement.autre,
            date_debut=_d(payload.date_debut),
            date_fin=_d(payload.date_fin),
            lieu=payload.lieu,
            description=payload.description,
        )
        validation.estampiller(e, auteur, role)
        s.add(e)
        s.flush()
        return _evenement_dict(s, e)


def update_evenement(campaign_id: str, evenement_id: int, payload: EvenementIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        e = s.get(Evenement, evenement_id)
        if not e:
            raise HTTPException(status_code=404, detail="Événement introuvable")
        data = payload.model_dump(exclude_unset=True)
        if "titre" in data and data["titre"] is not None:
            e.titre = data["titre"]
        if "type" in data and data["type"]:
            e.type = enums.TypeEvenement(data["type"])
        if "date_debut" in data:
            e.date_debut = _d(data["date_debut"])
        if "date_fin" in data:
            e.date_fin = _d(data["date_fin"])
        if "lieu" in data:
            e.lieu = data["lieu"]
        if "description" in data:
            e.description = data["description"]
        return _evenement_dict(s, e)


def delete_evenement(campaign_id: str, evenement_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        e = s.get(Evenement, evenement_id)
        if not e:
            raise HTTPException(status_code=404, detail="Événement introuvable")
        # Supprime d'abord les liaisons.
        for l in s.scalars(select(EvenementDepense).where(EvenementDepense.evenement_id == evenement_id)).all():
            s.delete(l)
        s.delete(e)
    return {"message": "Événement supprimé"}


def detail_evenement(campaign_id: str, evenement_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        e = s.get(Evenement, evenement_id)
        if not e:
            raise HTTPException(status_code=404, detail="Événement introuvable")
        depenses = [{
            "depense_id": dep.id,
            "num_piece": dep.num_piece,
            "libelle": dep.nature,
            "fournisseur": dep.fournisseur,
            "montant_ttc": dep.montant_ttc,
            "quote_part": l.quote_part,
            "cout_affecte": cout_affecte(l, dep),
        } for l, dep in depenses_liees(s, evenement_id)]
        documents = [{
            "id": doc.id,
            "type": doc.type.value,
            "fichier": doc.fichier,
            "enveloppe": doc.enveloppe.value if doc.enveloppe else None,
        } for doc in s.scalars(_valides(select(Document), Document).where(Document.evenement_id == evenement_id)).all()]
        d = _evenement_dict(s, e)
        d["depenses"] = depenses
        d["documents"] = documents
        return d


def _enveloppe_par_defaut(type_doc: enums.TypeDocument) -> enums.Enveloppe:
    """Une photo d'événement est une annexe (B) ; une facture, une pièce de A."""
    return enums.Enveloppe.B if type_doc == enums.TypeDocument.photo else enums.Enveloppe.A


def list_documents_evenement(campaign_id: str, evenement_id: int) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        docs = s.scalars(_valides(select(Document), Document).where(Document.evenement_id == evenement_id)).all()
        return [{
            "id": d.id,
            "type": d.type.value,
            "media_type": d.media_type,
            "fichier": d.fichier,
            "enveloppe": d.enveloppe.value if d.enveloppe else None,
            "date_ajout": d.date_ajout.isoformat() if d.date_ajout else None,
        } for d in docs]


def link_document(campaign_id: str, evenement_id: int, payload: DocumentEvenementIn,
                  auteur: str | None = None, role: str = ROLE_MANDATAIRE) -> dict:
    """Rattache une pièce à un événement, existante ou nouvellement téléversée."""
    ensure_campaign_db(campaign_id)
    try:
        type_doc = enums.TypeDocument(payload.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Type de pièce inconnu : {payload.type}")

    with campaign_session(campaign_id) as s:
        if not s.get(Evenement, evenement_id):
            raise HTTPException(status_code=404, detail="Événement introuvable")

        if payload.doc_id is not None:
            doc = s.get(Document, payload.doc_id)
            if not doc:
                raise HTTPException(status_code=404, detail="Pièce introuvable")
            # Pièce déjà classée (facture d'une dépense) : on ne touche pas à
            # son enveloppe, seulement à son rattachement.
            doc.evenement_id = evenement_id
        elif payload.fichier:
            fichier = os.path.basename(payload.fichier)
            doc = Document(
                type=type_doc,
                media_type=media_type(fichier),
                fichier=fichier,
                enveloppe=_enveloppe_par_defaut(type_doc),
                evenement_id=evenement_id,
            )
            validation.estampiller(doc, auteur, role)
            s.add(doc)
        else:
            raise HTTPException(status_code=400, detail="Fournir un fichier ou l'id d'une pièce existante")

    return detail_evenement(campaign_id, evenement_id)


def unlink_document(campaign_id: str, evenement_id: int, doc_id: int) -> dict:
    """Détache la pièce de l'événement. Le fichier et la pièce sont conservés :
    une facture rattachée à une dépense ne doit pas disparaître du dossier."""
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        doc = s.get(Document, doc_id)
        if doc and doc.evenement_id == evenement_id:
            doc.evenement_id = None
    return detail_evenement(campaign_id, evenement_id)


def link_depense(campaign_id: str, evenement_id: int, payload: LiaisonIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        if not s.get(Evenement, evenement_id):
            raise HTTPException(status_code=404, detail="Événement introuvable")
        if not s.get(Depense, payload.depense_id):
            raise HTTPException(status_code=404, detail="Dépense introuvable")
        # Contrôle : Σ quote-parts d'une dépense (tous événements) ≤ 100 %.
        autres = s.scalars(select(EvenementDepense).where(
            EvenementDepense.depense_id == payload.depense_id,
            EvenementDepense.evenement_id != evenement_id)).all()
        deja = sum(part(l.quote_part) for l in autres)
        nouvelle = part(payload.quote_part)
        if deja + nouvelle > QUOTE_PART_TOTALE:
            raise HTTPException(status_code=400,
                detail=f"Quote-part totale de cette dépense dépasserait 100 % (déjà affecté : {deja:.0f} %).")
        lien = s.get(EvenementDepense, {"evenement_id": evenement_id, "depense_id": payload.depense_id})
        if lien:
            lien.quote_part = payload.quote_part
        else:
            s.add(EvenementDepense(evenement_id=evenement_id, depense_id=payload.depense_id,
                                   quote_part=payload.quote_part))
    return detail_evenement(campaign_id, evenement_id)


def unlink_depense(campaign_id: str, evenement_id: int, depense_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        lien = s.get(EvenementDepense, {"evenement_id": evenement_id, "depense_id": depense_id})
        if lien:
            s.delete(lien)
    return detail_evenement(campaign_id, evenement_id)
