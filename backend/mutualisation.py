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
import os
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from db.models import DepenseMutualisee, Election, PartieExterne, RepartitionMutualisee
from db.session import campaign_session, ensure_campaign_db
from db.helpers import election_id as _election_id
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


# ── Convention PDF (reprend le template + le pipeline WeasyPrint de l'utilisateur) ─

def _pct(v) -> str:
    if v is None:
        return ""
    if float(v).is_integer():
        return f"{int(v)} %"
    return f"{v:.2f}".replace(".", ",") + " %"


def _montant(v) -> str:
    return f"{(v or 0):,.2f}".replace(",", " ").replace(".", ",")


_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "templates", "convention_mutualisation.html")


def convention_pdf(campaign_id: str, mut_id: int) -> bytes:
    # WeasyPrint a besoin de Pango/GLib (Homebrew) sur macOS.
    os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")
    from jinja2 import Template
    # macOS : Pango/GLib viennent de Homebrew (voir calendrier.export_pdf).
    os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")

    from weasyprint import HTML

    import identite
    ident = identite.get_identite(campaign_id)
    election = ident.get("election") or {}
    candidat = ident.get("candidat") or {}
    mandataire_d = ident.get("mandataire") or {}

    with campaign_session(campaign_id) as s:
        m = s.get(DepenseMutualisee, mut_id)
        if not m:
            raise HTTPException(status_code=404, detail="Dépense mutualisée introuvable")
        data = _mutualisee_dict(s, m)
        parties_ext = {p.id: p for p in s.scalars(select(PartieExterne)).all()}

    election_label = election.get("libelle") or "l'élection"
    mand_nom = " ".join(filter(None, [mandataire_d.get("civilite"), mandataire_d.get("prenom"),
                                      mandataire_d.get("nom")])).strip() or None
    cand_nom = " ".join(filter(None, [candidat.get("prenom"), candidat.get("nom")])).strip() or "Notre campagne"

    parties = []
    for r in data["repartitions"]:
        if r["partie"] == "notre_campagne":
            nom = cand_nom
            qualite = f"candidat aux {election_label}" if cand_nom != "Notre campagne" else ""
        else:
            pe = parties_ext.get(r["partie_id"])
            nom = (" ".join(filter(None, [pe.prenom_ou_liste, pe.nom])).strip() if pe else r["nom"])
            qualite = (f"candidat — {pe.scrutin}" if pe and pe.scrutin else "")
        parties.append({
            "nom": nom,
            "qualite": qualite,
            "pourcentage": _pct(r["pourcentage"]),
            "montant": _montant(r["montant"]),
        })

    justification = [ln.strip() for ln in (data["cle_justification"] or "").replace(";", "\n").splitlines()
                     if ln.strip()]

    context = {
        "conv_num": f"CONV-{mut_id:03d}",
        "election_label": election_label,
        "nature_depense": data["objet"],
        "description_depense": [f"{data['objet']} — {_montant(data['montant_total_ttc'])} € TTC"],
        "mandataire": mand_nom,
        "parties": parties,
        "justification": justification,
        "lieu": candidat.get("ville") or election.get("circonscription") or "",
        "date_signature": "__ ________ ____",
    }

    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        html = Template(f.read()).render(**context)
    return HTML(string=html).write_pdf()


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
