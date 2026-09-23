"""Constitution et dépôt du dossier (spec Bloc F).

Le compte se compose de deux enveloppes :
  - Enveloppe A : formulaire + toutes les pièces justificatives des dépenses
  - Enveloppe B : annexes (insérée dans A)

Ce module classe les pièces (Document) par enveloppe, produit l'état du dossier
(avec la checklist de conformité) et génère un bordereau de dépôt PDF.
"""

from __future__ import annotations

import io
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select

import calendrier
import conformite
from db.models import Document
from db.session import campaign_session, ensure_campaign_db
from database import UPLOADS_DIR
from db import enums

logger = logging.getLogger(__name__)

_TYPE_LABEL = {
    enums.TypeDocument.devis: "Devis",
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


def fichiers_rattaches(campaign_ids: list[str]) -> set[str]:
    """Noms de fichiers référencés par au moins un document, toutes campagnes.

    Le dossier `uploads` est commun aux campagnes : un fichier n'est orphelin
    que s'il n'est rattaché nulle part, pas seulement dans la campagne ouverte.
    """
    noms: set[str] = set()
    for campaign_id in campaign_ids:
        try:
            ensure_campaign_db(campaign_id)
            with campaign_session(campaign_id) as s:
                noms |= set(s.scalars(select(Document.fichier)).all())
        except Exception:
            logger.exception("Lecture des documents de %s impossible", campaign_id)
    return noms


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


ANNEXE_CALENDRIER = "B00_calendrier_de_campagne.pdf"


def _calendrier_annexe(campaign_id: str) -> Optional[bytes]:
    """Le calendrier, s'il y a quelque chose à représenter.

    Une campagne sans date de scrutin ni événement n'en produit pas : l'export
    du dossier ne doit pas échouer pour autant, l'annexe est simplement absente.
    """
    if calendrier.donnees(campaign_id)["vide"]:
        return None
    return calendrier.export_pdf(campaign_id)


def pieces_sans_fichier(campaign_id: str) -> list[str]:
    """Pièces référencées en base dont le fichier a disparu de `uploads`.

    Un dossier qui les contient part incomplet sans que rien ne le signale :
    le bordereau annonce une pièce que l'enveloppe ne contient pas.
    """
    presents = {p.name for p in Path(UPLOADS_DIR).iterdir() if p.is_file()}
    return sorted(d["fichier"] for d in list_documents(campaign_id)
                  if d["fichier"] and d["fichier"] not in presents)


def _nom_dans_archive(enveloppe: str, rang: int, fichier: str) -> str:
    """Nom préfixé par le numéro de pièce, pour retrouver l'ordre du bordereau."""
    return f"Enveloppe_{enveloppe}/{enveloppe}{rang:02d}_{fichier}"


def export_dossier_zip(campaign_id: str) -> bytes:
    """Dossier complet : bordereau en tête, puis les pièces classées par enveloppe.

    Les fichiers sont copiés tels quels — aucune recompression, aucune perte
    sur des justificatifs qui doivent rester lisibles par la commission.
    """
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("0_bordereau_de_depot.pdf", export_bordereau_pdf(campaign_id))

        etat = get_depot(campaign_id)
        annexe = _calendrier_annexe(campaign_id)
        if annexe:
            zf.writestr(f"Enveloppe_B/{ANNEXE_CALENDRIER}", annexe)
        for enveloppe, pieces in (("A", etat["pieces_A"]), ("B", etat["pieces_B"])):
            for rang, piece in enumerate(pieces, start=1):
                chemin = Path(UPLOADS_DIR) / (piece["fichier"] or "")
                if chemin.is_file():
                    zf.write(chemin, _nom_dans_archive(enveloppe, rang, chemin.name))
                else:
                    logger.warning("Pièce absente du disque, ignorée à l'export : %s",
                                   piece.get("fichier"))
    return tampon.getvalue()


def _safe(text: str, limit: int = 95) -> str:
    """Tronque et rend encodable par la police core de fpdf (latin-1)."""
    text = (text or "")[:limit]
    return text.encode("latin-1", "replace").decode("latin-1")


def _page_intercalaire(titre: str, sous_titre: str = "") -> bytes:
    """Page de séparation entre deux enveloppes, pour se repérer à l'impression."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.ln(100)
    pdf.cell(0, 12, _safe(titre, 60), align="C", new_x="LMARGIN", new_y="NEXT")
    if sous_titre:
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, _safe(sous_titre, 90), align="C", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _piece_en_pdf(chemin: Path, media_type: str) -> Optional[bytes]:
    """Ramène une pièce au format PDF, seul format assemblable.

    Une image est convertie en une page ; un PDF est repris tel quel. Les
    autres formats (tableur, texte) ne sont pas convertibles ici : ils restent
    dans l'archive ZIP, que le PDF fusionné ne remplace donc pas.
    """
    if media_type == "pdf":
        return chemin.read_bytes()
    if media_type == "image":
        from PIL import Image

        with Image.open(chemin) as img:
            tampon = io.BytesIO()
            img.convert("RGB").save(tampon, format="PDF")
            return tampon.getvalue()
    return None


def export_dossier_pdf(campaign_id: str) -> bytes:
    """Dossier complet en un seul PDF : bordereau, puis les pièces par enveloppe."""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()

    def ajouter(donnees: bytes) -> None:
        for page in PdfReader(io.BytesIO(donnees)).pages:
            writer.add_page(page)

    ajouter(export_bordereau_pdf(campaign_id))

    etat = get_depot(campaign_id)
    annexe_calendrier = _calendrier_annexe(campaign_id)
    non_convertibles: list[str] = []
    for enveloppe, pieces in (("A", etat["pieces_A"]), ("B", etat["pieces_B"])):
        annexes = 1 if (enveloppe == "B" and annexe_calendrier) else 0
        if not pieces and not annexes:
            continue
        ajouter(_page_intercalaire(f"ENVELOPPE {enveloppe}", f"{len(pieces) + annexes} pièce(s)"))
        if annexes:
            ajouter(_page_intercalaire("B00", "Calendrier de campagne"))
            ajouter(annexe_calendrier)
        for rang, piece in enumerate(pieces, start=1):
            chemin = Path(UPLOADS_DIR) / (piece["fichier"] or "")
            if not chemin.is_file():
                logger.warning("Pièce absente du disque, ignorée : %s", piece.get("fichier"))
                continue
            try:
                donnees = _piece_en_pdf(chemin, piece.get("media_type") or "")
            except Exception:
                logger.exception("Conversion impossible : %s", chemin.name)
                donnees = None
            if donnees is None:
                non_convertibles.append(f"{enveloppe}{rang:02d} — {chemin.name}")
                continue
            ajouter(_page_intercalaire(f"{enveloppe}{rang:02d}", chemin.name))
            ajouter(donnees)

    if non_convertibles:
        ajouter(_page_intercalaire(
            "PIECES NON INSEREES",
            "Formats non convertibles - voir l'archive ZIP : " + ", ".join(non_convertibles[:6]),
        ))

    sortie = io.BytesIO()
    writer.write(sortie)
    return sortie.getvalue()


def export_bordereau_pdf(campaign_id: str) -> bytes:
    """Bordereau de dépôt : liste des pièces par enveloppe + état de la checklist."""
    from fpdf import FPDF

    etat = get_depot(campaign_id)
    pdf = FPDF()
    pdf.add_page()
    printable = pdf.w - pdf.l_margin - pdf.r_margin

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
    # Annexe régénérée à chaque export : elle ne figure pas parmi les documents
    # stockés, mais elle est bien dans l'enveloppe.
    if not calendrier.donnees(campaign_id)["vide"]:
        pdf.set_font("helvetica", size=9)
        pdf.multi_cell(printable, 6, _safe("  + [Annexe generee] Calendrier de campagne"))
    if etat["pieces_non_classees"]:
        _section("PIÈCES NON CLASSÉES (à affecter à une enveloppe)", etat["pieces_non_classees"])

    out = pdf.output()
    return bytes(out)
