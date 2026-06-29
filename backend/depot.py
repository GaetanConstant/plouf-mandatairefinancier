"""Constitution et dépôt du dossier (spec Bloc F).

Le compte se compose de deux enveloppes :
  - Enveloppe A : formulaire + toutes les pièces justificatives des dépenses
  - Enveloppe B : annexes (insérée dans A)

Ce module classe les pièces (Document) par enveloppe, produit l'état du dossier
(avec la checklist de conformité) et génère un bordereau de dépôt PDF.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select

import conformite
from db.models import Document
from db.session import campaign_session, ensure_campaign_db
from db import enums

_TYPE_LABEL = {
    enums.TypeDocument.facture: "Facture",
    enums.TypeDocument.recu: "Reçu",
    enums.TypeDocument.releve_bancaire: "Relevé bancaire",
    enums.TypeDocument.recepisse: "Récépissé",
    enums.TypeDocument.photo: "Photo",
    enums.TypeDocument.contrat: "Contrat",
    enums.TypeDocument.statuts: "Statuts",
    enums.TypeDocument.autre: "Autre",
}


def _doc_dict(d: Document) -> dict:
    return {
        "id": d.id,
        "type": d.type.value if d.type else None,
        "type_label": _TYPE_LABEL.get(d.type, "Autre"),
        "fichier": d.fichier,
        "media_type": d.media_type,
        "enveloppe": d.enveloppe.value if d.enveloppe else None,
        "date_ajout": d.date_ajout.strftime("%Y-%m-%d") if d.date_ajout else None,
    }


def list_documents(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        docs = s.scalars(select(Document).order_by(Document.date_ajout.desc())).all()
        return [_doc_dict(d) for d in docs]


def set_document(campaign_id: str, doc_id: int, enveloppe: str | None, type_: str | None) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        d = s.get(Document, doc_id)
        if not d:
            raise HTTPException(status_code=404, detail="Document introuvable")
        if enveloppe is not None:
            d.enveloppe = enums.Enveloppe(enveloppe) if enveloppe else None
        if type_ is not None:
            d.type = enums.TypeDocument(type_)
        return _doc_dict(d)


def get_depot(campaign_id: str) -> dict:
    """État du dossier : pièces par enveloppe + checklist de conformité."""
    ensure_campaign_db(campaign_id)
    docs = list_documents(campaign_id)
    conf = conformite.run_checks(campaign_id)
    return {
        "pieces_A": [d for d in docs if d["enveloppe"] == "A"],
        "pieces_B": [d for d in docs if d["enveloppe"] == "B"],
        "pieces_non_classees": [d for d in docs if d["enveloppe"] not in ("A", "B")],
        "compteurs": conf["compteurs"],
        "alertes_bloquantes": [a for a in conf["alertes"] if a["niveau"] == "bloquant"],
        "pret_a_deposer": conf["pret_a_deposer"],
    }


def export_bordereau_pdf(campaign_id: str) -> bytes:
    """Bordereau de dépôt : liste des pièces par enveloppe + état de la checklist."""
    from fpdf import FPDF

    etat = get_depot(campaign_id)
    pdf = FPDF()
    pdf.add_page()
    printable = pdf.w - pdf.l_margin - pdf.r_margin

    def _safe(text: str, limit: int = 95) -> str:
        # Police core fpdf = latin-1 ; on remplace les caractères non encodables.
        text = (text or "")[:limit]
        return text.encode("latin-1", "replace").decode("latin-1")

    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 12, "BORDEREAU DE DÉPÔT DU COMPTE DE CAMPAGNE", ln=True, align="C")
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 8, f"Édité le {datetime.now().strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(4)

    statut = "PRÊT À DÉPOSER" if etat["pret_a_deposer"] else "NON PRÊT (points bloquants)"
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Statut : {statut}", ln=True)
    c = etat["compteurs"]
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 7, f"Bloquants : {c.get('bloquant', 0)}  -  "
                   f"Avertissements : {c.get('avertissement', 0)}  -  À compléter : {c.get('info', 0)}", ln=True)

    if etat["alertes_bloquantes"]:
        pdf.ln(2)
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, _safe("Points bloquants à corriger :"), ln=True)
        pdf.set_font("helvetica", size=9)
        for a in etat["alertes_bloquantes"]:
            pdf.multi_cell(printable, 6, _safe(f"  - {a['message']}"))

    def _section(titre, pieces):
        pdf.ln(3)
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 9, _safe(f"{titre} ({len(pieces)} pieces)"), ln=True)
        pdf.set_font("helvetica", size=9)
        if not pieces:
            pdf.cell(0, 6, _safe("  (aucune piece classee)"), ln=True)
            return
        for i, p in enumerate(pieces, 1):
            pdf.multi_cell(printable, 6, _safe(f"  {i}. [{p['type_label']}] {p['fichier']}"))

    _section("ENVELOPPE A - Formulaire + pièces justificatives des dépenses", etat["pieces_A"])
    _section("ENVELOPPE B - Annexes", etat["pieces_B"])
    if etat["pieces_non_classees"]:
        _section("PIÈCES NON CLASSÉES (à affecter à une enveloppe)", etat["pieces_non_classees"])

    out = pdf.output()
    return bytes(out)
