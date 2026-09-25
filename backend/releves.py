"""Relevés bancaires et rapprochement des dépenses.

Une transaction peut régler plusieurs dépenses, et une dépense peut être réglée
en plusieurs fois : le lien porte donc un montant imputé. Deux contrôles en
découlent, et ce sont eux qui font l'intérêt du module :

  - une transaction est **rapprochée** quand la somme de ses imputations égale
    son montant ;
  - une dépense est **soldée** quand la somme de ses imputations égale son TTC.

Aucune imputation ne peut dépasser l'un ou l'autre : le rapprochement ne doit
jamais faire apparaître plus d'argent qu'il n'en est sorti du compte.
"""

from __future__ import annotations

import csv
import io
import os
import logging
import re
import unicodedata
from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from db.helpers import fmt_date as _fmt, media_type, valides as _valides
from db.models import Depense, Document, ImputationBancaire, Releve, TransactionBancaire
from db.session import campaign_session, ensure_campaign_db
from db import enums
import validation
from database import ROLE_MANDATAIRE

logger = logging.getLogger(__name__)

# Tolérance de comparaison : les montants viennent de flottants et d'un OCR.
# Au centime près, sinon un écart d'arrondi ferait échouer un rapprochement juste.
TOLERANCE = 0.005


class TransactionIn(BaseModel):
    date_operation: str
    libelle: str
    montant: float
    sens: str = "debit"
    reference: Optional[str] = None


class ReleveIn(BaseModel):
    libelle: str
    source: str = "manuel"
    fichier: Optional[str] = None
    transactions: list[TransactionIn] = []


class ImputationIn(BaseModel):
    depense_id: int
    montant: Optional[float] = None  # None = solde restant de la dépense


# ── Lecture des formats ──────────────────────────────────────────────────────

_MOIS_COURTS = {m: i for i, m in enumerate(
    ["janv", "fevr", "mars", "avri", "mai", "juin",
     "juil", "aout", "sept", "octo", "nove", "dece"], start=1)}


def _sans_accent(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texte) if not unicodedata.combining(c))


def _lire_date(brut: str) -> Optional[date]:
    """Reconnaît les formats qu'une banque française peut produire."""
    brut = brut.strip()
    for motif in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(brut, motif).date()
        except ValueError:
            continue
    # « 08 sept. 2026 » et variantes issues d'un OCR.
    m = re.match(r"(\d{1,2})\s+([A-Za-zÀ-ÿ]{3,})\.?\s+(\d{4})", brut)
    if m:
        mois = _MOIS_COURTS.get(_sans_accent(m.group(2)).lower()[:4])
        if mois:
            return date(int(m.group(3)), mois, int(m.group(1)))
    return None


def _lire_montant(brut: str) -> Optional[float]:
    """Montant français ou anglo-saxon, avec signe éventuel."""
    texte = brut.strip().replace(" ", "").replace("\xa0", "").replace(" ", "").replace("€", "")
    if not texte:
        return None
    negatif = texte.startswith("-") or texte.endswith("-") or (texte.startswith("(") and texte.endswith(")"))
    texte = texte.strip("-()")
    # 1 234,56 → 1234.56 ; 1,234.56 → 1234.56
    if "," in texte and "." in texte:
        texte = texte.replace(".", "").replace(",", ".") if texte.rfind(",") > texte.rfind(".") \
            else texte.replace(",", "")
    else:
        texte = texte.replace(",", ".")
    try:
        valeur = float(texte)
    except ValueError:
        return None
    return -valeur if negatif else valeur


def lire_csv(contenu: bytes) -> list[dict]:
    """Extrait les transactions d'un CSV bancaire, sans présumer des en-têtes.

    Les banques n'exportent pas le même format ; on repère les colonnes par leur
    contenu (une date, un montant) plutôt que par leur nom.
    """
    texte = None
    for encodage in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texte = contenu.decode(encodage)
            break
        except UnicodeDecodeError:
            continue
    if texte is None:
        raise HTTPException(status_code=400, detail="Encodage du fichier non reconnu.")

    try:
        dialecte = csv.Sniffer().sniff(texte[:4096], delimiters=";,\t")
        separateur = dialecte.delimiter
    except csv.Error:
        separateur = ";" if texte.count(";") > texte.count(",") else ","

    lignes = []
    for champs in csv.reader(io.StringIO(texte), delimiter=separateur):
        if len(champs) < 2:
            continue
        jour = next((d for d in (_lire_date(c) for c in champs) if d), None)
        if jour is None:
            continue  # en-tête, solde, ligne de pied de relevé
        montants = [m for m in (_lire_montant(c) for c in champs[1:]) if m not in (None, 0.0)]
        if not montants:
            continue
        # Le libellé est le champ le plus long qui n'est ni date ni montant.
        candidats = [c.strip() for c in champs
                     if _lire_date(c) is None and _lire_montant(c) is None and c.strip()]
        montant = montants[0]
        lignes.append({
            "date_operation": jour.isoformat(),
            "libelle": max(candidats, key=len) if candidats else "Opération",
            "montant": abs(montant),
            "sens": "debit" if montant < 0 else "credit",
        })
    if not lignes:
        raise HTTPException(status_code=400,
                            detail="Aucune transaction reconnue dans ce fichier.")
    return lignes


def lire_texte(texte: str) -> list[dict]:
    """Extrait les transactions d'un texte libre : copier-coller ou sortie d'OCR.

    Une ligne exploitable porte une date et un montant ; ce qui reste au milieu
    est le libellé. Le résultat se relit avant import — un OCR se trompe.
    """
    lignes = []
    for ligne in texte.splitlines():
        if not ligne.strip():
            continue
        m_date = re.search(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}\s+[A-Za-zÀ-ÿ]{3,}\.?\s+\d{4}", ligne)
        if not m_date:
            continue
        jour = _lire_date(m_date.group(0))
        if jour is None:
            continue
        reste = ligne[m_date.end():]
        m_montant = None
        for m in re.finditer(r"-?\(?\d[\d  \xa0.,]*\d\)?-?\s*€?", reste):
            valeur = _lire_montant(m.group(0))
            if valeur not in (None, 0.0):
                m_montant = (m, valeur)
        if m_montant is None:
            continue
        m, montant = m_montant
        libelle = reste[:m.start()].strip(" \t|;:-") or "Opération"
        lignes.append({
            "date_operation": jour.isoformat(),
            "libelle": libelle,
            "montant": abs(montant),
            "sens": "debit" if montant < 0 else "credit",
        })
    if not lignes:
        raise HTTPException(status_code=400, detail="Aucune transaction reconnue dans ce texte.")
    return lignes


# ── Relevés ──────────────────────────────────────────────────────────────────

def _impute_sur_transaction(s, transaction_id: int) -> float:
    return s.scalar(select(func.coalesce(func.sum(ImputationBancaire.montant), 0.0))
                    .where(ImputationBancaire.transaction_id == transaction_id)) or 0.0


def _impute_sur_depense(s, depense_id: int) -> float:
    return s.scalar(select(func.coalesce(func.sum(ImputationBancaire.montant), 0.0))
                    .where(ImputationBancaire.depense_id == depense_id)) or 0.0


def _transaction_dict(s, t: TransactionBancaire) -> dict:
    impute = _impute_sur_transaction(s, t.id)
    imputations = []
    for i in s.scalars(select(ImputationBancaire)
                       .where(ImputationBancaire.transaction_id == t.id)).all():
        dep = s.get(Depense, i.depense_id)
        imputations.append({
            "id": i.id,
            "depense_id": i.depense_id,
            "montant": i.montant,
            "libelle_depense": dep.nature if dep else "Dépense supprimée",
            "fournisseur": dep.fournisseur if dep else None,
            "montant_depense": dep.montant_ttc if dep else None,
        })
    return {
        "id": t.id,
        "date_operation": _fmt(t.date_operation),
        "libelle": t.libelle,
        "montant": t.montant,
        "sens": t.sens.value,
        "reference": t.reference,
        "montant_impute": round(impute, 2),
        "reste": round(t.montant - impute, 2),
        "rapprochee": abs(t.montant - impute) < TOLERANCE,
        "imputations": imputations,
    }


def _releve_dict(s, r: Releve) -> dict:
    transactions = [_transaction_dict(s, t) for t in s.scalars(
        select(TransactionBancaire)
        .where(TransactionBancaire.releve_id == r.id)
        .order_by(TransactionBancaire.date_operation)).all()]
    # Seuls les débits se rapprochent de dépenses : compter les crédits
    # empêcherait le compteur de tomber à zéro sur un relevé qui en porte un.
    debits = [t for t in transactions if t["sens"] == "debit"]
    rapprochees = sum(1 for t in debits if t["rapprochee"])
    return {
        "id": r.id,
        "libelle": r.libelle,
        "source": r.source.value,
        "date_debut": _fmt(r.date_debut),
        "date_fin": _fmt(r.date_fin),
        "importe_par": r.importe_par,
        "importe_le": r.importe_le.isoformat() if r.importe_le else None,
        "nb_transactions": len(transactions),
        "nb_rapprochables": len(debits),
        "nb_rapprochees": rapprochees,
        "nb_orphelines": len(debits) - rapprochees,
        "total_debit": round(sum(t["montant"] for t in transactions if t["sens"] == "debit"), 2),
        "total_credit": round(sum(t["montant"] for t in transactions if t["sens"] == "credit"), 2),
        "transactions": transactions,
    }


def list_releves(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        releves = s.scalars(select(Releve).order_by(Releve.date_debut.desc())).all()
        return [_releve_dict(s, r) for r in releves]


def create_releve(campaign_id: str, payload: ReleveIn, auteur: str) -> dict:
    """Enregistre un relevé et ses transactions, toutes conservées.

    Les lignes sans dépense en face — frais bancaires, encaissement d'un don —
    restent au relevé et ressortent comme non rapprochées.
    """
    ensure_campaign_db(campaign_id)
    try:
        source = enums.SourceReleve(payload.source)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Source inconnue : {payload.source}")
    if not payload.transactions:
        raise HTTPException(status_code=400, detail="Un relevé sans transaction n'a rien à rapprocher.")

    jours = [_lire_date(t.date_operation) for t in payload.transactions]
    if any(j is None for j in jours):
        raise HTTPException(status_code=400, detail="Une transaction porte une date illisible.")

    with campaign_session(campaign_id) as s:
        # Le relevé lui-même est une pièce du dossier : le guide l'exige en
        # enveloppe B, « eux seuls permettent de s'assurer du règlement effectif
        # des dépenses ». Sans le fichier d'origine, l'import reste possible
        # mais la pièce manquera au dépôt.
        if payload.fichier:
            fichier = os.path.basename(payload.fichier)
            piece = Document(
                type=enums.TypeDocument.releve_bancaire,
                media_type=media_type(fichier),
                fichier=fichier,
                enveloppe=enums.Enveloppe.B,
            )
            validation.estampiller(piece, auteur, ROLE_MANDATAIRE)
            s.add(piece)

        releve = Releve(
            libelle=payload.libelle, source=source, fichier=payload.fichier,
            date_debut=min(jours), date_fin=max(jours),
            importe_par=auteur, importe_le=datetime.now(),
        )
        s.add(releve)
        s.flush()
        for t, jour in zip(payload.transactions, jours):
            s.add(TransactionBancaire(
                releve_id=releve.id, date_operation=jour, libelle=t.libelle.strip()[:255],
                montant=abs(t.montant),
                sens=enums.SensTransaction(t.sens if t.sens in ("debit", "credit") else "debit"),
                reference=t.reference,
            ))
        s.flush()
        return _releve_dict(s, releve)


def delete_releve(campaign_id: str, releve_id: int) -> dict:
    """Supprime un relevé, ses transactions et leurs rapprochements.

    Les dépenses que ce relevé réglait redeviennent non rapprochées : la
    cascade efface les imputations sans rien dire aux dépenses, qui resteraient
    sinon « payées » en pointant un relevé disparu.
    """
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        r = s.get(Releve, releve_id)
        if not r:
            return {"message": "Relevé supprimé."}
        concernees = list(s.scalars(
            select(ImputationBancaire.depense_id)
            .join(TransactionBancaire, TransactionBancaire.id == ImputationBancaire.transaction_id)
            .where(TransactionBancaire.releve_id == releve_id)).all())
        s.delete(r)
        s.flush()
        for depense_id in set(concernees):
            depense = s.get(Depense, depense_id)
            if depense:
                _actualiser_depense(s, depense, None)
    return {"message": "Relevé supprimé."}


# ── Rapprochement ────────────────────────────────────────────────────────────

def imputer(campaign_id: str, transaction_id: int, payload: ImputationIn) -> dict:
    """Affecte une part de transaction à une dépense.

    Refuse tout ce qui ferait dépasser le montant de la transaction ou le TTC de
    la dépense : un rapprochement ne doit jamais faire apparaître plus d'argent
    qu'il n'en est sorti du compte.
    """
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        t = s.get(TransactionBancaire, transaction_id)
        if not t:
            raise HTTPException(status_code=404, detail="Transaction introuvable")
        if t.sens != enums.SensTransaction.debit:
            raise HTTPException(
                status_code=400,
                detail="Cette ligne est un encaissement : elle ne peut pas régler une dépense.")
        d = s.get(Depense, payload.depense_id)
        if not d:
            raise HTTPException(status_code=404, detail="Dépense introuvable")

        reste_transaction = round(t.montant - _impute_sur_transaction(s, t.id), 2)
        reste_depense = round((d.montant_ttc or 0.0) - _impute_sur_depense(s, d.id), 2)
        montant = payload.montant if payload.montant is not None else min(reste_transaction, reste_depense)
        montant = round(montant, 2)

        if montant <= 0:
            raise HTTPException(status_code=400, detail="Le montant imputé doit être positif.")
        if montant > reste_transaction + TOLERANCE:
            raise HTTPException(
                status_code=400,
                detail=f"Il ne reste que {reste_transaction:.2f} € à imputer sur cette transaction.")
        if montant > reste_depense + TOLERANCE:
            raise HTTPException(
                status_code=400,
                detail=f"Il ne reste que {reste_depense:.2f} € à régler sur cette dépense.")

        s.add(ImputationBancaire(transaction_id=t.id, depense_id=d.id, montant=montant))
        s.flush()
        _actualiser_depense(s, d, t)
        return _transaction_dict(s, t)


def _actualiser_depense(s, depense: Depense, transaction: Optional[TransactionBancaire]) -> None:
    """Répercute l'état du rapprochement sur la dépense elle-même.

    Une dépense intégralement imputée est réglée : c'est le relevé qui le dit,
    plus une case cochée à la main.
    """
    impute = _impute_sur_depense(s, depense.id)
    soldee = abs((depense.montant_ttc or 0.0) - impute) < TOLERANCE
    depense.rapprochement = soldee
    if soldee:
        depense.reglee = True
        depense.statut = enums.StatutDepense.paye
        if transaction is not None:
            depense.num_releve_bancaire = transaction.releve.libelle
    else:
        # Plus rien ne la règle entièrement : elle redevient une facture en
        # attente. On ne restaure pas un éventuel statut « engagé » d'origine,
        # que le rapprochement n'a pas mémorisé — mais laisser « payée » une
        # dépense sans ligne bancaire fausserait la trésorerie et le dossier.
        depense.reglee = False
        depense.num_releve_bancaire = None
        if depense.statut == enums.StatutDepense.paye:
            depense.statut = enums.StatutDepense.facture


def desimputer(campaign_id: str, imputation_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        i = s.get(ImputationBancaire, imputation_id)
        if not i:
            raise HTTPException(status_code=404, detail="Imputation introuvable")
        transaction_id, depense_id = i.transaction_id, i.depense_id
        s.delete(i)
        s.flush()
        d = s.get(Depense, depense_id)
        if d:
            _actualiser_depense(s, d, None)
        t = s.get(TransactionBancaire, transaction_id)
        return _transaction_dict(s, t) if t else {"message": "Imputation retirée."}


def depenses_a_rapprocher(campaign_id: str) -> list[dict]:
    """Dépenses qu'il reste à régler, avec ce qui a déjà été imputé."""
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        lignes = []
        for d in s.scalars(_valides(select(Depense), Depense)
                           .order_by(Depense.date_facture)).all():
            impute = _impute_sur_depense(s, d.id)
            reste = round((d.montant_ttc or 0.0) - impute, 2)
            if reste <= TOLERANCE:
                continue
            lignes.append({
                "id": d.id,
                "date_facture": _fmt(d.date_facture),
                "libelle": d.nature,
                "fournisseur": d.fournisseur,
                "montant_ttc": d.montant_ttc,
                "montant_impute": round(impute, 2),
                "reste": reste,
            })
        return lignes


def paiements_par_depense(campaign_id: str) -> dict[int, dict]:
    """Pour chaque dépense rapprochée : date du dernier paiement et libellé du relevé.

    Alimente la main courante, qui doit montrer la facture et son règlement
    côte à côte.
    """
    ensure_campaign_db(campaign_id)
    resultat: dict[int, dict] = {}
    with campaign_session(campaign_id) as s:
        for i in s.scalars(select(ImputationBancaire)).all():
            t = s.get(TransactionBancaire, i.transaction_id)
            if not t:
                continue
            courant = resultat.get(i.depense_id)
            if courant is None or t.date_operation > courant["_date"]:
                resultat[i.depense_id] = {
                    "_date": t.date_operation,
                    "date_paiement": _fmt(t.date_operation),
                    "libelle_releve": t.libelle,
                }
    return {k: {"date_paiement": v["date_paiement"], "libelle_releve": v["libelle_releve"]}
            for k, v in resultat.items()}
