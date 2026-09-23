"""Service comptable : pont entre l'API (contrat legacy) et le modèle ORM.

Les endpoints conservent le même JSON qu'avant (compatibilité frontend), mais
les données sont désormais lues/écrites dans la base SQLite ORM d'une campagne.
"""

from __future__ import annotations

import logging
import os
import unicodedata

from fastapi import HTTPException
from sqlalchemy import func, select

from db.models import Depense, Document, Donateur, Election, Recette
from db.session import campaign_session, ensure_campaign_db
from db.helpers import fmt_date as _fmt_date, media_type as _media_type
from db import enums
from database import UPLOADS_DIR

logger = logging.getLogger(__name__)

PLAFOND_LEGAL_DEFAUT = 154781.0
TAUX_REMBOURSEMENT = 0.475
LIMITE_DON_INDIVIDUEL = 4600.0

# Rubrique 7xxx par catégorie de recette.
_RUBRIQUE_RECETTE = {
    enums.CategorieRecette.don: "7010",
    enums.CategorieRecette.apport_perso: "7020",
    enums.CategorieRecette.pret: "7030",
    enums.CategorieRecette.contribution_parti: "7040",
}

# Statut dépense ORM ↔ libellé legacy affiché par le frontend.
_STATUT_TO_LEGACY = {
    enums.StatutDepense.paye: "Payé",
    enums.StatutDepense.facture: "Facturé",
    enums.StatutDepense.engage: "Engagé",
    enums.StatutDepense.realise_nature: "Réalisé (Nature)",
}


def _norm(s: str | None) -> str:
    s = (s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _type_to_categorie(type_legacy: str | None) -> enums.CategorieRecette:
    t = _norm(type_legacy)
    if t.startswith("don"):
        return enums.CategorieRecette.don
    if t.startswith("apport"):
        return enums.CategorieRecette.apport_perso
    if t.startswith("pret"):
        return enums.CategorieRecette.pret
    if "parti" in t:
        return enums.CategorieRecette.contribution_parti
    return enums.CategorieRecette.don


def _categorie_to_type(cat: enums.CategorieRecette) -> str:
    if cat == enums.CategorieRecette.don:
        return "Don"
    if cat == enums.CategorieRecette.apport_perso:
        return "Apport"
    return "Pret"


def _statut_legacy_to_orm(statut: str | None, is_nature: bool) -> tuple[enums.StatutDepense, bool]:
    if is_nature:
        return enums.StatutDepense.realise_nature, False
    s = _norm(statut)
    if s == "paye":
        return enums.StatutDepense.paye, True
    if s == "facture":
        return enums.StatutDepense.facture, False
    return enums.StatutDepense.engage, False






# ── Recettes ─────────────────────────────────────────────────────────────────

def _recette_to_legacy(r: Recette) -> dict:
    return {
        "id": r.id,
        "date": _fmt_date(r.date_versement),
        "nom_donateur": r.donateur.nom if r.donateur else None,
        "adresse": r.donateur.adresse if r.donateur else None,
        "montant": r.montant,
        "type": _categorie_to_type(r.categorie),
        "recu_genere": r.recu_genere,
        "date_envoi": r.date_envoi,
    }


def list_recettes(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        recettes = s.scalars(select(Recette).order_by(Recette.date_versement.desc())).all()
        return [_recette_to_legacy(r) for r in recettes]


def _get_or_create_donateur(s, nom: str, adresse: str | None) -> Donateur:
    don = s.scalars(select(Donateur).where(Donateur.nom == nom)).first()
    if don is None:
        don = Donateur(nom=nom, adresse=adresse, est_personne_physique=True)
        s.add(don)
        s.flush()
    elif adresse and not don.adresse:
        don.adresse = adresse
    return don


def create_recette(campaign_id: str, dto) -> dict:
    ensure_campaign_db(campaign_id)
    categorie = _type_to_categorie(dto.type)
    with campaign_session(campaign_id) as s:
        don = _get_or_create_donateur(s, dto.nom_donateur, dto.adresse)
        # Contrôle du plafond de 4 600 € par donateur (dons uniquement).
        if categorie == enums.CategorieRecette.don:
            deja = s.scalar(
                select(func.coalesce(func.sum(Recette.montant), 0.0))
                .where(Recette.donateur_id == don.id, Recette.categorie == enums.CategorieRecette.don)
            )
            if deja + dto.montant > LIMITE_DON_INDIVIDUEL:
                raise HTTPException(
                    status_code=400,
                    detail=f"Le donateur {dto.nom_donateur} dépasse le plafond de "
                           f"{LIMITE_DON_INDIVIDUEL}€ (Déjà donné: {deja}€)",
                )
        r = Recette(
            donateur=don,
            categorie=categorie,
            montant=dto.montant,
            date_versement=dto.date,
            mode=None,
            rubrique_imputation=_RUBRIQUE_RECETTE.get(categorie, "7050"),
            recu_genere=getattr(dto, "recu_genere", False) or False,
            date_envoi=getattr(dto, "date_envoi", None),
        )
        s.add(r)
    return {"message": "Recette ajoutée"}


def update_recette(campaign_id: str, recette_id: int, dto) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        r = s.get(Recette, recette_id)
        if not r:
            raise HTTPException(status_code=404, detail="Recette introuvable")
        r.categorie = _type_to_categorie(dto.type)
        r.montant = dto.montant
        r.date_versement = dto.date
        r.rubrique_imputation = _RUBRIQUE_RECETTE.get(r.categorie, "7050")
        don = _get_or_create_donateur(s, dto.nom_donateur, dto.adresse)
        # Mise à jour de l'adresse même si le donateur en avait déjà une.
        if dto.adresse:
            don.adresse = dto.adresse
        r.donateur = don
    return {"message": "Recette mise à jour"}


def toggle_recette_sent(campaign_id: str, recette_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    from datetime import datetime
    with campaign_session(campaign_id) as s:
        r = s.get(Recette, recette_id)
        if not r:
            raise HTTPException(status_code=404, detail="Recette introuvable")
        if r.date_envoi:
            r.date_envoi = None
            r.recu_genere = False
            return {"message": "Marquage annulé", "date_envoi": None}
        today = datetime.now().strftime("%d/%m/%Y %H:%M")
        r.date_envoi = today
        r.recu_genere = True
        return {"message": "Attestation marquée comme envoyée", "date_envoi": today}


def get_recette_pdf_data(campaign_id: str, recette_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        r = s.get(Recette, recette_id)
        if not r:
            raise HTTPException(status_code=404, detail="Recette introuvable")
        d = r.date_versement
        return {
            "id": r.id,
            "date": d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else (str(d) if d else "N/A"),
            "nom_donateur": r.donateur.nom if r.donateur else "",
            "adresse": (r.donateur.adresse if r.donateur else "") or "",
            "montant": r.montant,
            "type": _categorie_to_type(r.categorie),
        }


# ── Dépenses ─────────────────────────────────────────────────────────────────

def _supprimer_fichier_remplace(session, ancien: str | None, nouveau: str) -> None:
    """Efface du disque le fichier qu'une pièce vient de remplacer.

    Ne supprime que si plus aucun document de la campagne ne le référence : un
    même fichier peut avoir été rattaché à deux dépenses. Un échec d'effacement
    n'interrompt pas la mise à jour — on perd un fichier orphelin, pas la
    comptabilité ; l'écran Justificatifs le signalera.
    """
    if not ancien or ancien == nouveau:
        return
    encore_reference = session.scalar(
        select(func.count()).select_from(Document).where(Document.fichier == ancien)
    )
    if encore_reference:
        return
    chemin = os.path.join(UPLOADS_DIR, ancien)
    try:
        os.remove(chemin)
        logger.info("Pièce remplacée supprimée du disque : %s", ancien)
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.warning("Suppression de %s impossible : %s", chemin, e)


def _type_piece(valeur: str | None) -> enums.TypeDocument:
    """Nature de la pièce jointe à une dépense (devis, facture…).

    Une valeur inconnue vaut `facture` : la saisie ne doit pas échouer sur un
    libellé, le classement du dépôt reste corrigeable depuis l'écran Dépôt.
    """
    try:
        return enums.TypeDocument(valeur) if valeur else enums.TypeDocument.facture
    except ValueError:
        return enums.TypeDocument.facture


def _depense_to_legacy(d: Depense, doc_fichier: str | None, doc_type: str | None = None) -> dict:
    return {
        "id": d.id,
        "date": _fmt_date(d.date_reglement),
        "libelle": d.nature,
        "fournisseur": d.fournisseur,
        "montant_ttc": d.montant_ttc,
        "tva": d.tva,
        "categorie_cnccfp": d.rubrique_imputation,
        "statut": _STATUT_TO_LEGACY.get(d.statut, "Engagé"),
        "justificatif_path": doc_fichier,
        "type_piece": doc_type or enums.TypeDocument.facture.value,
        "is_nature": d.statut == enums.StatutDepense.realise_nature,
    }


def list_depenses(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        depenses = s.scalars(select(Depense).order_by(Depense.date_reglement.desc())).all()
        # Pré-charge les fichiers de justificatif.
        doc_ids = {d.facture_doc_id for d in depenses if d.facture_doc_id}
        docs = {}
        if doc_ids:
            for doc in s.scalars(select(Document).where(Document.id.in_(doc_ids))).all():
                docs[doc.id] = (doc.fichier, doc.type.value)
        resultat = []
        for d in depenses:
            fichier, type_doc = docs.get(d.facture_doc_id, (None, None))
            resultat.append(_depense_to_legacy(d, fichier, type_doc))
        return resultat


def create_depense(campaign_id: str, dto) -> dict:
    ensure_campaign_db(campaign_id)
    statut, reglee = _statut_legacy_to_orm(dto.statut, dto.is_nature)
    with campaign_session(campaign_id) as s:
        facture_doc_id = None
        if dto.justificatif_path:
            fichier = os.path.basename(dto.justificatif_path)
            doc = Document(
                type=_type_piece(dto.type_piece),
                media_type=_media_type(fichier),
                fichier=fichier,
                enveloppe=enums.Enveloppe.A,
            )
            s.add(doc)
            s.flush()
            facture_doc_id = doc.id
        s.add(Depense(
            fournisseur=dto.fournisseur,
            nature=dto.libelle,
            montant_ttc=dto.montant_ttc,
            tva=dto.tva,
            date_reglement=dto.date,
            mode=None,
            rubrique_imputation=dto.categorie_cnccfp,
            statut=statut,
            reglee=reglee,
            facture_doc_id=facture_doc_id,
        ))
    return {"message": "Dépense ajoutée"}


def update_depense(campaign_id: str, depense_id: int, dto) -> dict:
    """Met à jour une dépense existante (date, fournisseur, montant, pièce…).

    La pièce jointe est remplacée **en place** : un devis qui devient facture
    garde la même ligne de document, sinon le devis resterait listé dans le
    dépôt comme une pièce orpheline. Sans nouveau fichier, seule sa nature est
    mise à jour — le justificatif déjà rattaché n'est jamais détaché.
    """
    ensure_campaign_db(campaign_id)
    statut, reglee = _statut_legacy_to_orm(dto.statut, dto.is_nature)
    type_piece = _type_piece(dto.type_piece)
    with campaign_session(campaign_id) as s:
        d = s.get(Depense, depense_id)
        if not d:
            raise HTTPException(status_code=404, detail="Dépense introuvable")

        doc = s.get(Document, d.facture_doc_id) if d.facture_doc_id else None
        if dto.justificatif_path:
            fichier = os.path.basename(dto.justificatif_path)
            if doc is None:
                doc = Document(
                    type=type_piece,
                    media_type=_media_type(fichier),
                    fichier=fichier,
                    enveloppe=enums.Enveloppe.A,
                )
                s.add(doc)
                s.flush()
                d.facture_doc_id = doc.id
            else:
                ancien = doc.fichier
                doc.fichier = fichier
                doc.media_type = _media_type(fichier)
                doc.type = type_piece
                s.flush()
                _supprimer_fichier_remplace(s, ancien, fichier)
        elif doc is not None:
            doc.type = type_piece

        d.fournisseur = dto.fournisseur
        d.nature = dto.libelle
        d.montant_ttc = dto.montant_ttc
        d.tva = dto.tva
        d.date_reglement = dto.date
        d.rubrique_imputation = dto.categorie_cnccfp
        d.statut = statut
        d.reglee = reglee
    return {"message": "Dépense mise à jour"}


def list_fournisseurs(campaign_id: str) -> list[str]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        rows = s.scalars(
            select(Depense.fournisseur)
            .where(Depense.fournisseur.is_not(None), Depense.fournisseur != "")
            .distinct()
            .order_by(Depense.fournisseur.asc())
        ).all()
        return list(rows)


def get_depense_pdf_data(campaign_id: str, depense_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        d = s.get(Depense, depense_id)
        if not d:
            raise HTTPException(status_code=404, detail="Dépense introuvable")
        dt = d.date_reglement
        return {
            "id": d.id,
            "date": dt.strftime("%d/%m/%Y") if hasattr(dt, "strftime") else (str(dt) if dt else "N/A"),
            "libelle": d.nature,
            "fournisseur": d.fournisseur,
            "montant_ttc": d.montant_ttc,
            "tva": d.tva or 0.0,
            "categorie_cnccfp": d.rubrique_imputation,
        }


# ── Statistiques (tableau de bord) ───────────────────────────────────────────

def compute_stats(campaign_id: str) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        total_depenses = s.scalar(select(func.coalesce(func.sum(Depense.montant_ttc), 0.0))) or 0.0
        total_depenses_payees = s.scalar(
            select(func.coalesce(func.sum(Depense.montant_ttc), 0.0))
            .where(Depense.statut == enums.StatutDepense.paye)
        ) or 0.0
        total_nature = s.scalar(
            select(func.coalesce(func.sum(Depense.montant_ttc), 0.0))
            .where(Depense.statut == enums.StatutDepense.realise_nature)
        ) or 0.0
        total_recettes = s.scalar(select(func.coalesce(func.sum(Recette.montant), 0.0))) or 0.0
        nombre_donateurs = s.scalar(
            select(func.count(func.distinct(Recette.donateur_id)))
            .where(Recette.categorie == enums.CategorieRecette.don)
        ) or 0
        election = s.scalars(select(Election)).first()
        plafond = (election.plafond_depenses if election and election.plafond_depenses
                   else PLAFOND_LEGAL_DEFAUT)

    consommation = (total_depenses / plafond) * 100 if plafond else 0.0
    estimation_remboursement = min((total_depenses - total_nature) * TAUX_REMBOURSEMENT,
                                   plafond * TAUX_REMBOURSEMENT)
    reste_a_depenser = plafond - total_depenses
    solde_tresorerie = total_recettes - total_depenses_payees
    solde_previsionnel = total_recettes - (total_depenses - total_nature)
    if total_recettes > 0:
        consommation_budget_actuel = (total_depenses_payees / total_recettes) * 100
    else:
        consommation_budget_actuel = 0.0 if total_depenses_payees == 0 else 100.0

    return {
        "total_depenses": total_depenses,
        "total_depenses_payees": total_depenses_payees,
        "total_recettes": total_recettes,
        "plafond": plafond,
        "consommation_plafond": consommation,
        "estimation_remboursement": estimation_remboursement,
        "reste_a_depenser": reste_a_depenser,
        "nombre_donateurs": nombre_donateurs,
        "solde_tresorerie": solde_tresorerie,
        "solde_previsionnel": solde_previsionnel,
        "consommation_budget_actuel": consommation_budget_actuel,
        "total_nature_hors_tresorerie": total_nature,
    }


def export_csv_rows(campaign_id: str) -> tuple[list[dict], list[dict]]:
    """Retourne (depenses, recettes) au format legacy pour l'export CSV."""
    return list_depenses(campaign_id), list_recettes(campaign_id)
