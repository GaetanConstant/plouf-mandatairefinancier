"""Complétude du dossier : ce qui empêche un dépôt, et ce qui n'y entre pas."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import completude
import comptes
from datetime import date
from models import Depense, Recette
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


def _section(cid, cle):
    return {s["cle"]: s for s in completude.evaluer(cid)["sections"]}[cle]


def test_depense_sans_facture_compte_dans_le_restant():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 2, 10), libelle="Location véhicule", fournisseur="F",
            montant_ttc=145.13, tva=0.0, categorie_cnccfp="D1", statut="Facturé"))
        sec = _section(cid, "justificatifs_depenses")
        assert sec["requis"] == 1 and sec["remplis"] == 0, sec
        # Repérable par son numéro de pièce : c'est par lui qu'on classe.
        assert sec["manquants"] == ["D001 — Location véhicule (145 €)"], sec["manquants"]
    finally:
        teardown(cid)


def test_depense_avec_facture_ne_compte_pas():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 2, 10), libelle="Impression", fournisseur="F",
            montant_ttc=900.0, tva=0.0, categorie_cnccfp="A1", statut="Facturé",
            justificatif_path="facture.pdf"))
        sec = _section(cid, "justificatifs_depenses")
        assert sec["complet"] and sec["remplis"] == 1, sec
    finally:
        teardown(cid)


def test_concours_en_nature_n_exige_pas_de_facture():
    """Une prestation donnée n'a pas de facture — même exception que la conformité."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 2, 10), libelle="Salle prêtée", fournisseur="Mairie",
            montant_ttc=300.0, tva=0.0, categorie_cnccfp="B1", statut="Payé",
            is_nature=True))
        sec = _section(cid, "justificatifs_depenses")
        assert sec["requis"] == 0 and sec["complet"], sec
    finally:
        teardown(cid)


def test_recette_sans_justificatif_compte_dans_le_restant():
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, Recette(
            date=date(2026, 2, 10), nom_donateur="DUPONT Jean", adresse="1 rue X",
            montant=2000.0, type="Pret"))
        sec = _section(cid, "justificatifs_recettes")
        assert sec["requis"] == 1 and sec["remplis"] == 0, sec
        assert sec["manquants"] == ["R001 — Prêt (2000 €)"], sec["manquants"]
    finally:
        teardown(cid)


def test_justificatifs_manquants_bloquent_l_export():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 2, 10), libelle="Location", fournisseur="F",
            montant_ttc=145.0, tva=0.0, categorie_cnccfp="D1", statut="Facturé"))
        etat = completude.evaluer(cid)
        assert any("Justificatifs de dépenses" in m for m in etat["manquants"]), etat["manquants"]
    finally:
        teardown(cid)


def test_depense_non_validee_hors_decompte():
    """Ce qui attend l'arbitrage n'est pas encore une étape du dossier."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 2, 10), libelle="Bière", fournisseur="Cave",
            montant_ttc=22.82, tva=0.0, categorie_cnccfp="B2", statut="Facturé"),
            auteur="militant", role="equipe")
        sec = _section(cid, "justificatifs_depenses")
        assert sec["requis"] == 0, sec
    finally:
        teardown(cid)


def test_piece_deposee_sur_une_recette_sort_du_restant():
    """La section recettes doit être actionnable : sinon elle bloque l'export à vie."""
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, Recette(
            date=date(2026, 2, 10), nom_donateur="DUPONT Jean", adresse="1 rue X",
            montant=500.0, type="Don"))
        rec = comptes.list_recettes(cid)[0]
        assert not _section(cid, "justificatifs_recettes")["complet"]

        comptes.ajouter_piece_recette(
            cid, rec["id"], comptes.PieceIn(fichier="recu_001.pdf", type_piece="recu"),
            auteur="gaetan", role="mandataire")

        assert _section(cid, "justificatifs_recettes")["complet"]
        assert comptes.list_recettes(cid)[0]["justificatif_path"] == "recu_001.pdf"
    finally:
        teardown(cid)


def test_recette_creee_avec_sa_piece():
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, Recette(
            date=date(2026, 2, 10), nom_donateur="MARTIN Claire", adresse="2 rue Y",
            montant=300.0, type="Don", justificatif_path="recu_002.pdf"))
        assert _section(cid, "justificatifs_recettes")["complet"]
    finally:
        teardown(cid)


def test_chaque_manque_porte_de_quoi_le_traiter():
    """Un manque sans action est un constat : l'écran ne saurait pas quoi proposer."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 2, 10), libelle="Location", fournisseur="F",
            montant_ttc=145.0, tva=0.0, categorie_cnccfp="D1", statut="Facturé"))
        comptes.create_recette(cid, Recette(
            date=date(2026, 2, 10), nom_donateur="DUPONT Jean", adresse="1 rue X",
            montant=500.0, type="Don"))
        sans_action = [s["titre"] for s in completude.evaluer(cid)["sections"]
                       if not s["complet"] and not s["actions"]]
        assert not sans_action, sans_action
    finally:
        teardown(cid)


def test_action_de_depense_porte_son_identifiant():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 2, 10), libelle="Location", fournisseur="Rent",
            montant_ttc=145.0, tva=0.0, categorie_cnccfp="D1", statut="Facturé"))
        depense_id = comptes.list_depenses(cid)[0]["id"]
        action = _section(cid, "justificatifs_depenses")["actions"][0]
        assert action["type"] == "depense" and action["id"] == depense_id, action
        assert action["num_piece"] == "D001" and action["tiers"] == "Rent", action
    finally:
        teardown(cid)


def test_action_disparait_une_fois_la_piece_deposee():
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, Recette(
            date=date(2026, 2, 10), nom_donateur="DUPONT Jean", adresse="1 rue X",
            montant=500.0, type="Don"))
        rec = comptes.list_recettes(cid)[0]
        comptes.ajouter_piece_recette(
            cid, rec["id"], comptes.PieceIn(fichier="recu.pdf", type_piece="recu"),
            auteur="gaetan", role="mandataire")
        assert _section(cid, "justificatifs_recettes")["actions"] == []
    finally:
        teardown(cid)


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
