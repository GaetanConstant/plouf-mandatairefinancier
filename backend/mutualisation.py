"""Dépenses mutualisées entre candidats + conventions (spec §6.13, §8).

Règle clé : seule NOTRE quote-part constitue notre dépense électorale. Le montant
total avancé n'est jamais inscrit comme dépense de notre compte. La clé de
répartition et les flux entre mandataires sont retracés dans l'état des dépenses
mutualisées joint au compte.

NB : le générateur de conventions historique (conventions/generate_convention.py,
WeasyPrint) reste disponible pour les rendus enrichis à 2 candidats. Ici la
convention est produite en PDF léger (fpdf2) directement depuis la base, pour un
nombre quelconque de parties.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from db.models import DepenseMutualisee, Election, PartieExterne, RepartitionMutualisee
from db.session import campaign_session, ensure_campaign_db
from db import enums


class PartieExterneIn(BaseModel):
    nom: str
    prenom_ou_liste: Optional[str] = None
    scrutin: Optional[str] = None
    circonscription: Optional[str] = None
    mandataire_contact: Optional[str] = None
    adresse: Optional[str] = None
    email: Optional[str] = None


class RepartitionIn(BaseModel):
    partie: str  # notre_campagne | partie_externe
    partie_id: Optional[int] = None
    pourcentage: float
    statut_reglement: Optional[str] = None


class MutualiseeIn(BaseModel):
    objet: str
    montant_total_ttc: float
    cle_justification: Optional[str] = None
    porteur: str = "notre_campagne"  # qui avance le paiement
    porteur_partie_id: Optional[int] = None
    evenement_id: Optional[int] = None
    depense_id: Optional[int] = None
    repartitions: list[RepartitionIn] = []


def _election_id(s) -> Optional[int]:
    e = s.scalars(select(Election)).first()
    return e.id if e else None


# ── Parties externes ─────────────────────────────────────────────────────────

def list_parties(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        parties = s.scalars(select(PartieExterne).order_by(PartieExterne.nom)).all()
        return [{"id": p.id, "nom": p.nom, "prenom_ou_liste": p.prenom_ou_liste,
                 "scrutin": p.scrutin, "circonscription": p.circonscription,
                 "mandataire_contact": p.mandataire_contact, "adresse": p.adresse,
                 "email": p.email} for p in parties]


def create_partie(campaign_id: str, payload: PartieExterneIn) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        p = PartieExterne(**payload.model_dump())
        s.add(p)
        s.flush()
        return {"id": p.id, "message": "Partie externe créée"}


# ── Dépenses mutualisées ─────────────────────────────────────────────────────

def _mutualisee_dict(s, m: DepenseMutualisee) -> dict:
    reps = s.scalars(select(RepartitionMutualisee).where(
        RepartitionMutualisee.depense_mutualisee_id == m.id)).all()
    parties = {p.id: p.nom for p in s.scalars(select(PartieExterne)).all()}
    repartitions = []
    notre_part = 0.0
    for r in reps:
        montant = (m.montant_total_ttc or 0.0) * (r.pourcentage or 0.0) / 100.0
        if r.partie == enums.PartieMutualisee.notre_campagne:
            notre_part = montant
        repartitions.append({
            "id": r.id,
            "partie": r.partie.value,
            "partie_id": r.partie_id,
            "nom": "Notre campagne" if r.partie == enums.PartieMutualisee.notre_campagne else parties.get(r.partie_id, "Partie externe"),
            "pourcentage": r.pourcentage,
            "montant": round(montant, 2),
            "statut_reglement": r.statut_reglement.value if r.statut_reglement else None,
        })
    return {
        "id": m.id,
        "objet": m.objet,
        "montant_total_ttc": m.montant_total_ttc,
        "cle_justification": m.cle_justification,
        "porteur": m.porteur.value if m.porteur else None,
        "porteur_partie_id": m.porteur_partie_id,
        "evenement_id": m.evenement_id,
        "depense_id": m.depense_id,
        "notre_quote_part": round(notre_part, 2),
        "repartitions": repartitions,
    }


def list_mutualisees(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        muts = s.scalars(select(DepenseMutualisee)).all()
        return [_mutualisee_dict(s, m) for m in muts]


def create_mutualisee(campaign_id: str, payload: MutualiseeIn) -> dict:
    ensure_campaign_db(campaign_id)
    total_pct = sum(r.pourcentage for r in payload.repartitions)
    if payload.repartitions and abs(total_pct - 100.0) > 0.01:
        raise HTTPException(status_code=400,
            detail=f"La somme des pourcentages de répartition doit faire 100 % (actuel : {total_pct:.1f} %).")
    with campaign_session(campaign_id) as s:
        m = DepenseMutualisee(
            election_id=_election_id(s),
            objet=payload.objet,
            montant_total_ttc=payload.montant_total_ttc,
            cle_justification=payload.cle_justification,
            porteur=enums.PorteurMutualise(payload.porteur),
            porteur_partie_id=payload.porteur_partie_id,
            evenement_id=payload.evenement_id,
            depense_id=payload.depense_id,
        )
        s.add(m)
        s.flush()
        for r in payload.repartitions:
            s.add(RepartitionMutualisee(
                depense_mutualisee_id=m.id,
                partie=enums.PartieMutualisee(r.partie),
                partie_id=r.partie_id,
                pourcentage=r.pourcentage,
                montant=(payload.montant_total_ttc or 0.0) * r.pourcentage / 100.0,
                statut_reglement=enums.StatutReglementMutualise(r.statut_reglement) if r.statut_reglement
                else enums.StatutReglementMutualise.sans_objet,
            ))
        s.flush()
        return _mutualisee_dict(s, m)


def delete_mutualisee(campaign_id: str, mut_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        m = s.get(DepenseMutualisee, mut_id)
        if not m:
            raise HTTPException(status_code=404, detail="Dépense mutualisée introuvable")
        for r in s.scalars(select(RepartitionMutualisee).where(
                RepartitionMutualisee.depense_mutualisee_id == mut_id)).all():
            s.delete(r)
        s.delete(m)
    return {"message": "Dépense mutualisée supprimée"}


# ── Convention PDF ───────────────────────────────────────────────────────────

def _safe(text, limit: int = 110) -> str:
    return str(text if text is not None else "")[:limit].encode("latin-1", "replace").decode("latin-1")


def convention_pdf(campaign_id: str, mut_id: int) -> bytes:
    from fpdf import FPDF

    with campaign_session(campaign_id) as s:
        m = s.get(DepenseMutualisee, mut_id)
        if not m:
            raise HTTPException(status_code=404, detail="Dépense mutualisée introuvable")
        data = _mutualisee_dict(s, m)

    pdf = FPDF()
    pdf.add_page()
    printable = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("helvetica", "B", 15)
    pdf.cell(0, 12, _safe("CONVENTION DE DÉPENSE MUTUALISÉE"), ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("helvetica", size=11)
    pdf.multi_cell(printable, 7, _safe(f"Objet : {data['objet']}"))
    pdf.cell(0, 7, _safe(f"Montant total TTC : {data['montant_total_ttc']:.2f} EUR"), ln=True)
    pdf.ln(2)

    if data["cle_justification"]:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 7, _safe("Clé de répartition :"), ln=True)
        pdf.set_font("helvetica", size=10)
        pdf.multi_cell(printable, 6, _safe(data["cle_justification"], 600))
        pdf.ln(2)

    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, _safe("Répartition entre les parties :"), ln=True)
    pdf.set_font("helvetica", size=10)
    for r in data["repartitions"]:
        pdf.multi_cell(printable, 6, _safe(
            f"  - {r['nom']} : {r['pourcentage']:.2f} %  ->  {r['montant']:.2f} EUR  ({r['statut_reglement'] or 'sans objet'})"))

    pdf.ln(8)
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 7, _safe(f"Fait le {datetime.now().strftime('%d/%m/%Y')}"), ln=True)
    pdf.ln(10)
    for r in data["repartitions"]:
        pdf.cell(0, 12, _safe(f"Signature {r['nom']} : ______________________"), ln=True)

    return bytes(pdf.output())


# ── État des dépenses mutualisées (Excel) ────────────────────────────────────

def export_etat_xlsx(campaign_id: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    muts = list_mutualisees(campaign_id)
    wb = Workbook()
    ws = wb.active
    ws.title = "Dépenses mutualisées"
    ws.append(["Objet", "Montant total TTC", "Clé de répartition", "Partie",
               "Pourcentage", "Montant dû (€)", "Statut règlement"])
    for m in muts:
        for r in m["repartitions"]:
            ws.append([m["objet"], m["montant_total_ttc"], m["cle_justification"],
                       r["nom"], r["pourcentage"], r["montant"], r["statut_reglement"]])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
