"""Notes de frais : les avances d'une personne, regroupées en un document.

Une personne qui avance dix petites sommes dans le mois attend un seul
virement et un seul papier à signer. La note rassemble ses dépenses, se
télécharge en PDF, et se solde par un unique mouvement bancaire.

Son état n'est pas stocké. Elle est remboursée quand toutes ses dépenses sont
rapprochées au relevé : c'est le compte qui l'atteste. Une case cochée en plus
finirait tôt ou tard par contredire les chiffres.
"""

from __future__ import annotations

import io
import os
from datetime import date
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from database import ROLE_MANDATAIRE, UPLOADS_DIR
from db.helpers import election_id as _election_id, fmt_date as _fmt, media_type, valides as _valides
from db.models import Depense, Document, NoteFrais
from db.session import campaign_session, ensure_campaign_db
from db import enums
import validation


class NoteFraisIn(BaseModel):
    personne: str
    commentaire: Optional[str] = None
    # Dépenses retenues ; vide = toutes les avances non remboursées de la personne.
    depense_ids: Optional[list[int]] = None


class PieceNoteIn(BaseModel):
    """Preuve du remboursement : virement, reçu signé."""
    fichier: str


def _note_dict(s, n: NoteFrais) -> dict:
    lignes = list(s.scalars(_valides(select(Depense), Depense)
                            .where(Depense.note_frais_id == n.id)
                            .order_by(Depense.date_facture)).all())
    total = round(sum(d.montant_ttc or 0.0 for d in lignes), 2)
    # Remboursée quand le compte a réglé toutes ses lignes, pas avant.
    remboursee = bool(lignes) and all(d.rapprochement for d in lignes)
    doc = s.get(Document, n.justificatif_doc_id) if n.justificatif_doc_id else None
    return {
        "id": n.id,
        "personne": n.personne,
        "date_creation": _fmt(n.date_creation),
        "commentaire": n.commentaire,
        "total": total,
        "nb_lignes": len(lignes),
        "remboursee": remboursee,
        "justificatif": doc.fichier if doc else None,
        "lignes": [{
            "id": d.id, "num_piece": d.num_piece, "date": _fmt(d.date_facture),
            "libelle": d.nature, "fournisseur": d.fournisseur,
            "montant": d.montant_ttc, "rapprochee": d.rapprochement,
        } for d in lignes],
    }


def list_notes(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        return [_note_dict(s, n) for n in s.scalars(
            select(NoteFrais).order_by(NoteFrais.date_creation.desc(), NoteFrais.id.desc())).all()]


def create_note(campaign_id: str, payload: NoteFraisIn) -> dict:
    """Crée la note d'une personne à partir de ses avances non remboursées."""
    ensure_campaign_db(campaign_id)
    personne = (payload.personne or "").strip()
    if not personne:
        raise HTTPException(status_code=400, detail="Indiquez la personne concernée.")

    with campaign_session(campaign_id) as s:
        requete = (_valides(select(Depense), Depense)
                   .where(Depense.avance_par == personne,
                          Depense.note_frais_id.is_(None)))
        if payload.depense_ids:
            requete = requete.where(Depense.id.in_(payload.depense_ids))
        # Une dépense déjà remboursée n'a plus rien à réclamer.
        lignes = [d for d in s.scalars(requete).all() if not d.rapprochement]
        if not lignes:
            raise HTTPException(
                status_code=400,
                detail=f"Aucune avance à rembourser pour {personne}.")

        note = NoteFrais(election_id=_election_id(s), personne=personne,
                         date_creation=date.today(), commentaire=payload.commentaire)
        s.add(note)
        s.flush()
        for d in lignes:
            d.note_frais_id = note.id
        s.flush()
        return _note_dict(s, note)


def delete_note(campaign_id: str, note_id: int) -> dict:
    """Supprime la note et rend ses dépenses à l'état d'avances libres.

    Les dépenses ne sont jamais supprimées : elles existent indépendamment du
    document qui les regroupe.
    """
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        note = s.get(NoteFrais, note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note de frais introuvable")
        for d in s.scalars(select(Depense).where(Depense.note_frais_id == note_id)).all():
            d.note_frais_id = None
        s.delete(note)
    return {"message": "Note de frais supprimée ; les dépenses sont conservées."}


def attacher_piece(campaign_id: str, note_id: int, fichier: str, auteur: str) -> dict:
    """Rattache la preuve du remboursement — virement, reçu signé."""
    ensure_campaign_db(campaign_id)
    nom = os.path.basename(fichier)
    with campaign_session(campaign_id) as s:
        note = s.get(NoteFrais, note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note de frais introuvable")
        doc = Document(
            type=enums.TypeDocument.autre,
            media_type=media_type(nom),
            fichier=nom,
            enveloppe=enums.Enveloppe.A,
        )
        validation.estampiller(doc, auteur, ROLE_MANDATAIRE)
        s.add(doc)
        s.flush()
        note.justificatif_doc_id = doc.id
    return {"message": "Justificatif rattaché à la note."}


def _texte(valeur, limite: int = 60) -> str:
    """Tronque et rend encodable par la police de base de fpdf (latin-1)."""
    return str(valeur or "")[:limite].encode("latin-1", "replace").decode("latin-1")


def export_pdf(campaign_id: str, note_id: int) -> bytes:
    """La note à imprimer et faire signer, avec le détail et le total."""
    from fpdf import FPDF

    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        note = s.get(NoteFrais, note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note de frais introuvable")
        donnees = _note_dict(s, note)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 12, "NOTE DE FRAIS", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("helvetica", size=11)
    pdf.cell(0, 7, _texte(donnees["personne"], 90), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 7, f"Etablie le {donnees['date_creation'] or ''}",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    pdf.set_font("helvetica", "B", 9)
    for largeur, titre in ((22, "Piece"), (24, "Date"), (62, "Objet"),
                           (48, "Fournisseur"), (26, "Montant")):
        pdf.cell(largeur, 8, titre, border=1)
    pdf.ln()

    pdf.set_font("helvetica", size=9)
    for l in donnees["lignes"]:
        pdf.cell(22, 7, _texte(l["num_piece"], 10), border=1)
        pdf.cell(24, 7, _texte(l["date"], 12), border=1)
        pdf.cell(62, 7, _texte(l["libelle"], 38), border=1)
        pdf.cell(48, 7, _texte(l["fournisseur"], 28), border=1)
        pdf.cell(26, 7, f"{(l['montant'] or 0):.2f} EUR", border=1, align="R")
        pdf.ln()

    pdf.set_font("helvetica", "B", 10)
    pdf.cell(156, 8, "TOTAL A REMBOURSER", border=1, align="R")
    pdf.cell(26, 8, f"{donnees['total']:.2f} EUR", border=1, align="R")
    pdf.ln(14)

    if donnees["commentaire"]:
        pdf.set_font("helvetica", size=9)
        pdf.multi_cell(0, 5, _texte(donnees["commentaire"], 400))
        pdf.ln(4)

    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 7, "Je certifie avoir avance les sommes ci-dessus pour le compte de la campagne.",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.cell(95, 7, "Date :", new_x="RIGHT")
    pdf.cell(95, 7, "Signature :", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
