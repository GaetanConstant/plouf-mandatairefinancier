"""Annexes CNCCFP : colistiers (liste), équipe de campagne (Annexe 7),
emprunts (Annexes 3.2 / 3.3 / 3.4).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select

import os

from db.models import Colistier, Document, Election, Emprunt, MembreEquipe, Recette
from db.session import campaign_session, ensure_campaign_db
from db.helpers import election_id as _election_id, fmt_date as _fmt, media_type
from db import enums
from database import ROLE_MANDATAIRE
import validation


def _type_document(valeur: str | None) -> enums.TypeDocument:
    """Nature de la pièce ; un contrat de prêt en est un par défaut."""
    try:
        return enums.TypeDocument(valeur) if valeur else enums.TypeDocument.contrat
    except ValueError:
        return enums.TypeDocument.contrat


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


def _fichier_contrat(s, doc_id) -> Optional[str]:
    if not doc_id:
        return None
    doc = s.get(Document, doc_id)
    return doc.fichier if doc else None


_TYPE_PAR_DEFAUT = {
    enums.CategorieRecette.contribution_parti: enums.TypeEmprunt.parti,
}


def emprunt_de_recette(campaign_id: str, recette_id: int, fichier: str,
                       type_piece: str = "contrat", auteur: str = "",
                       role: str = ROLE_MANDATAIRE) -> dict:
    """Dépose le contrat d'un prêt, en créant l'emprunt s'il n'existe pas.

    Une recette de type « prêt » n'était reliée à aucun emprunt : la colonne
    `Recette.emprunt_id` existait sans que rien ne l'alimente, et l'onglet
    Emprunts vivait à côté de la comptabilité. Le contrat écrit étant exigé,
    c'est lui qui déclenche la création — le prêteur, le montant et la date
    sont repris de la recette, le reste se complète dans l'onglet Emprunts.
    """
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        r = s.get(Recette, recette_id)
        if not r:
            raise HTTPException(status_code=404, detail="Recette introuvable")
        if r.categorie != enums.CategorieRecette.pret:
            raise HTTPException(
                status_code=400,
                detail="Cette recette n'est pas un prêt : elle n'appelle pas de contrat.")

        doc = Document(
            type=_type_document(type_piece),
            media_type=media_type(fichier),
            fichier=os.path.basename(fichier),
            enveloppe=enums.Enveloppe.A,
        )
        validation.estampiller(doc, auteur, role)
        s.add(doc)
        s.flush()

        emprunt = s.get(Emprunt, r.emprunt_id) if r.emprunt_id else None
        if emprunt is None:
            nom = r.donateur.nom if r.donateur else None
            emprunt = Emprunt(
                election_id=_election_id(s),
                type=_TYPE_PAR_DEFAUT.get(r.categorie, enums.TypeEmprunt.personne_physique),
                preteur_nom=nom,
                date_contrat=r.date_versement,
                montant=r.montant,
            )
            s.add(emprunt)
            s.flush()
            r.emprunt_id = emprunt.id
        emprunt.contrat_doc_id = doc.id

    return {"message": "Contrat de prêt rattaché."}


def list_emprunts(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        rows = s.scalars(select(Emprunt).order_by(Emprunt.date_contrat)).all()
        return [{"id": e.id, "type": e.type.value if e.type else None,
                 "preteur_nom": e.preteur_nom, "preteur_civilite": e.preteur_civilite,
                 "preteur_prenom": e.preteur_prenom, "preteur_pays": e.preteur_pays,
                 "date_contrat": _fmt(e.date_contrat), "duree_mois": e.duree_mois,
                 "date_fin": _fmt(e.date_fin), "taux": e.taux, "montant": e.montant,
                 "contrat_doc_id": e.contrat_doc_id,
                 "contrat_fichier": _fichier_contrat(s, e.contrat_doc_id)}
                for e in rows]


def _recette_de_l_emprunt(s, e: Emprunt) -> None:
    """Inscrit l'emprunt en recette, pour qu'il entre dans la comptabilité.

    Un emprunt saisi dans son onglet n'apparaissait ni dans les recettes ni
    dans la main courante : les deux vivaient côte à côte sans se connaître.
    Or un prêt est bien de l'argent entré sur le compte, et doit figurer en
    rubrique 7030 comme n'importe quelle recette.
    """
    import comptes
    import pieces
    import validation as _validation

    nom = (e.preteur_nom or "").strip() or "Prêteur à préciser"
    if e.preteur_prenom:
        nom = f"{nom} {e.preteur_prenom}".strip()
    donateur = comptes._get_or_create_donateur(s, nom, None)
    # Une banque ou un parti n'est pas une personne physique : le distinguer
    # importe pour les contrôles de dons et la liste des donateurs.
    donateur.est_personne_physique = (e.type == enums.TypeEmprunt.personne_physique)

    r = Recette(
        donateur=donateur,
        categorie=enums.CategorieRecette.pret,
        montant=e.montant,
        date_versement=e.date_contrat or date.today(),
        rubrique_imputation="7030",
        emprunt_id=e.id,
    )
    _validation.estampiller(r, None, ROLE_MANDATAIRE)
    s.add(r)
    s.flush()
    pieces.attribuer(s, r)


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
        _recette_de_l_emprunt(s, e)
        return {"id": e.id,
                "message": "Emprunt ajouté, et inscrit en recette."}


def delete_emprunt(campaign_id: str, emprunt_id: int) -> dict:
    """Supprime le contrat d'emprunt, et détache la recette qui en venait.

    La recette n'est pas supprimée : l'argent est bien entré sur le compte, et
    l'effacer d'office fausserait les totaux. Elle redevient un prêt ordinaire,
    qu'on requalifie ou qu'on supprime séparément.
    """
    ensure_campaign_db(campaign_id)
    detachees = 0
    with campaign_session(campaign_id) as s:
        e = s.get(Emprunt, emprunt_id)
        if not e:
            return {"message": "Emprunt supprimé"}
        for r in s.scalars(select(Recette).where(Recette.emprunt_id == emprunt_id)).all():
            r.emprunt_id = None
            detachees += 1
        s.delete(e)
    return {"message": "Emprunt supprimé."
                       + (f" La recette correspondante est conservée." if detachees else "")}
