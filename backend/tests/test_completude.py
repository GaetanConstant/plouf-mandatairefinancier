"""Complétude du dossier : ce qui empêche un dépôt, et ce qui n'y entre pas."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import completude
from db.session import campaign_session
from db.models import Colistier, ExpertComptable
from db.helpers import election_id
from routers.depot import _exiger_dossier_complet
from _fixture import fresh_campaign, teardown, run_tests


def _colistiers(cid, civilites, ordres=None):
    ordres = ordres or list(range(1, len(civilites) + 1))
    with campaign_session(cid) as s:
        eid = election_id(s)
        for rang, civ in zip(ordres, civilites):
            s.add(Colistier(election_id=eid, ordre=rang, civilite=civ, nom=f"NOM{rang}"))


def test_campagne_neuve_incomplete():
    cid = fresh_campaign()
    try:
        etat = completude.evaluer(cid)
        assert not etat["complet"]
        assert etat["pct"] < 100
        titres = {s["cle"]: s for s in etat["sections"]}
        assert titres["candidat"]["remplis"] == 0
        assert titres["expert_comptable"]["remplis"] == 0
    finally:
        teardown(cid)


def test_expert_dispense_compte_comme_complet():
    """La dispense est une réponse valable : elle ne doit pas peser comme un vide."""
    cid = fresh_campaign()
    try:
        avant = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["expert_comptable"]
        assert not avant["complet"]

        with campaign_session(cid) as s:
            s.add(ExpertComptable(election_id=election_id(s), dispense=True))

        apres = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["expert_comptable"]
        assert apres["complet"]
    finally:
        teardown(cid)


def test_alternance_rompue_signalee():
    cid = fresh_campaign()
    try:
        _colistiers(cid, ["M.", "Mme", "Mme", "M."])
        liste = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["liste"]
        assert "Alternance femme / homme rompue" in liste["manquants"]
    finally:
        teardown(cid)


def test_rangs_non_continus_signales():
    cid = fresh_campaign()
    try:
        _colistiers(cid, ["M.", "Mme", "M."], ordres=[1, 2, 7])
        liste = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["liste"]
        assert "Rangs non continus à partir de 1" in liste["manquants"]
    finally:
        teardown(cid)


def test_export_refuse_sur_dossier_incomplet():
    """Le refus porte la liste des manques : l'écran l'affiche telle quelle."""
    cid = fresh_campaign()
    try:
        try:
            _exiger_dossier_complet(cid)
        except HTTPException as e:
            assert e.status_code == 409
            assert e.detail["manquants"], "le refus doit dire ce qui manque"
        else:
            raise AssertionError("un dossier vide doit refuser l'export")
    finally:
        teardown(cid)


def test_export_pdf_assemble_bordereau_et_pieces():
    """Le PDF fusionné doit embarquer les pièces, pas seulement les annoncer."""
    import io

    from pypdf import PdfReader

    import depot
    from database import UPLOADS_DIR
    from db.models import Document
    from db import enums
    from pathlib import Path as _Path

    cid = fresh_campaign()
    piece = _Path(UPLOADS_DIR) / "piece_test_export.pdf"
    try:
        # Une pièce PDF minimale, produite par la même brique que le bordereau.
        from fpdf import FPDF
        doc_pdf = FPDF()
        doc_pdf.add_page()
        doc_pdf.set_font("helvetica", size=12)
        doc_pdf.cell(0, 10, "Facture de test")
        piece.write_bytes(bytes(doc_pdf.output()))

        with campaign_session(cid) as s:
            s.add(Document(type=enums.TypeDocument.facture, media_type="pdf",
                           fichier=piece.name, enveloppe=enums.Enveloppe.A))

        pages_bordereau = len(PdfReader(io.BytesIO(depot.export_bordereau_pdf(cid))).pages)
        pages_dossier = len(PdfReader(io.BytesIO(depot.export_dossier_pdf(cid))).pages)
        # Bordereau + intercalaire enveloppe + intercalaire pièce + la pièce.
        assert pages_dossier > pages_bordereau
    finally:
        piece.unlink(missing_ok=True)
        teardown(cid)


def test_piece_sans_fichier_bloque_le_depot():
    """Le bordereau annoncerait une pièce que l'enveloppe ne contiendrait pas."""
    from db.models import Document
    from db import enums

    cid = fresh_campaign()
    try:
        with campaign_session(cid) as s:
            s.add(Document(type=enums.TypeDocument.facture, media_type="pdf",
                           fichier="fichier_qui_nexiste_pas.pdf", enveloppe=enums.Enveloppe.A))

        pieces = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["pieces"]
        assert not pieces["complet"]
        assert any("fichier_qui_nexiste_pas.pdf" in m for m in pieces["manquants"])
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
