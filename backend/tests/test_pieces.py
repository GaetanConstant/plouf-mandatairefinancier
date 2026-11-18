"""Numérotation des pièces comptables : attribution, stabilité, propagation."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import comptes
import depot
import maincourante
import pieces
from db.models import Depense as DepenseORM
from db.session import campaign_session
from models import Depense, Recette
from _fixture import fresh_campaign, teardown, run_tests


def _depense(libelle="Test", montant=100.0, d="2026-01-10", justificatif=None):
    return Depense(date=date.fromisoformat(d), libelle=libelle, fournisseur="Four",
                   montant_ttc=montant, tva=0.0, categorie_cnccfp="A1", statut="Payé",
                   is_nature=False, justificatif_path=justificatif)


def _recette(montant=100.0, nom="DUPONT Jean", d="2026-01-10"):
    return Recette(date=date.fromisoformat(d), nom_donateur=nom, adresse="1 rue X",
                   montant=montant, type="Don")


def test_numero_attribue_a_la_creation():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(libelle="Première"))
        comptes.create_depense(cid, _depense(libelle="Deuxième"))
        par_libelle = {d["libelle"]: d["num_piece"] for d in comptes.list_depenses(cid)}
        assert par_libelle == {"Première": "D001", "Deuxième": "D002"}, par_libelle
    finally:
        teardown(cid)


def test_recettes_et_depenses_numerotees_separement():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense())
        comptes.create_recette(cid, _recette())
        assert comptes.list_depenses(cid)[0]["num_piece"] == "D001"
        assert comptes.list_recettes(cid)[0]["num_piece"] == "R001"
    finally:
        teardown(cid)


def test_suppression_ne_reattribue_pas_un_numero():
    """Un numéro déjà porté par une pièce archivée ne doit jamais resservir.

    Le compteur suit le plus grand rang atteint, pas le nombre de lignes : sinon
    la dépense suivante reprendrait le numéro écrit sur une facture au dossier.
    """
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(libelle="A"))
        comptes.create_depense(cid, _depense(libelle="B"))
        with campaign_session(cid) as s:
            s.delete(s.get(DepenseORM, 2))
        comptes.create_depense(cid, _depense(libelle="C"))
        par_libelle = {d["libelle"]: d["num_piece"] for d in comptes.list_depenses(cid)}
        assert par_libelle["C"] == "D003", par_libelle
    finally:
        teardown(cid)


def test_numero_stable_apres_modification():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(libelle="A", d="2026-03-01"))
        comptes.create_depense(cid, _depense(libelle="B", d="2026-01-01"))
        avant = {d["libelle"]: d["num_piece"] for d in comptes.list_depenses(cid)}
        depense_a = next(d for d in comptes.list_depenses(cid) if d["libelle"] == "A")
        comptes.update_depense(cid, depense_a["id"],
                               _depense(libelle="A", montant=999.0, d="2025-12-01"))
        apres = {d["libelle"]: d["num_piece"] for d in comptes.list_depenses(cid)}
        assert apres == avant, (avant, apres)
    finally:
        teardown(cid)


def test_numero_repris_dans_la_main_courante():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense())
        comptes.create_recette(cid, _recette())
        numeros = {l["sens"]: l["num_piece"] for l in maincourante.journal(cid)}
        assert numeros == {"depense": "D001", "recette": "R001"}, numeros
    finally:
        teardown(cid)


def test_justificatif_classe_sous_le_numero_de_sa_depense():
    """Le fichier de l'enveloppe porte le numéro qu'annonce le journal."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(justificatif="facture_edf.pdf"))
        piece = depot.get_depot(cid)["pieces_A"][0]
        assert piece["num_piece"] == "D001", piece
        nom = depot._nom_dans_archive("A", 1, piece["fichier"], piece["num_piece"])
        assert nom == "Enveloppe_A/D001_facture_edf.pdf", nom
    finally:
        teardown(cid)


def test_piece_declarative_garde_son_rang():
    """Sans écriture rattachée, pas de numéro de pièce : le rang fait foi."""
    assert depot._nom_dans_archive("B", 3, "statuts.pdf", None) == "Enveloppe_B/B03_statuts.pdf"


def test_rang_tolere_un_numero_illisible():
    assert pieces.rang(None) == 0
    assert pieces.rang("") == 0
    assert pieces.rang("ancien-format") == 0
    assert pieces.rang("D042") == 42


def _releve(cid, statut=None) -> int:
    """Relevé PDF de l'enveloppe B, comme le dépose l'onglet Relevés."""
    from db import enums
    from db.models import Document
    with campaign_session(cid) as s:
        doc = Document(type=enums.TypeDocument.releve_bancaire, media_type="pdf",
                       fichier="releve_octobre.pdf", enveloppe=enums.Enveloppe.B,
                       periode="2026-10")
        if statut:
            doc.statut_validation = statut
        s.add(doc)
        s.flush()
        return doc.id


def test_releve_reutilise_justifie_plusieurs_frais():
    """Un relevé qui justifie plusieurs frais bancaires reste une seule pièce.

    Chaque dépense sort des manques ; la pièce n'est rangée qu'une fois, en B,
    porte tous les numéros qu'elle justifie, et le bordereau renvoie vers elle.
    """
    import completude
    import conformite
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(libelle="Frais ouverture"))
        comptes.create_depense(cid, _depense(libelle="Cotisation carte"))
        comptes.create_depense(cid, _depense(libelle="Facture", justificatif="facture.pdf"))
        releve = _releve(cid)
        for dep in comptes.list_depenses(cid):
            if dep["libelle"] != "Facture":
                comptes.reutiliser_piece(cid, dep["id"], releve)

        section = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["justificatifs_depenses"]
        assert section["complet"], section["manquants"]
        codes = [a["code"] for a in conformite.run_checks(cid)["alertes"]]
        assert "justificatif_manquant" not in codes, codes

        etat = depot.get_depot(cid)
        assert [p["fichier"] for p in etat["pieces_B"]] == ["releve_octobre.pdf"]
        assert etat["pieces_B"][0]["num_pieces"] == ["D001", "D002"]
        # La facture de D003 garde son propre numéro, pas celui du relevé.
        assert [p["num_piece"] for p in etat["pieces_A"]] == ["D003"]
        assert [r["num_piece"] for r in etat["renvois"]] == ["D001", "D002"]
        assert all(r["enveloppe"] == "B" for r in etat["renvois"])
    finally:
        teardown(cid)


def test_reutiliser_refuse_une_piece_non_validee():
    """Une pièce encore « proposée » par l'équipe ne justifie rien."""
    from fastapi import HTTPException
    from db import enums
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(libelle="Frais"))
        releve = _releve(cid, statut=enums.StatutValidation.propose)
        try:
            comptes.reutiliser_piece(cid, comptes.list_depenses(cid)[0]["id"], releve)
        except HTTPException as e:
            assert e.status_code == 409
        else:
            raise AssertionError("une pièce non validée ne doit pas être réutilisable")
        assert comptes.list_depenses(cid)[0]["justificatif_path"] is None
    finally:
        teardown(cid)


def test_zip_contient_les_tableurs_du_compte():
    """Le ZIP est tout ce qu'on envoie : pièces, bordereau et tableurs."""
    import io
    import zipfile
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(justificatif="facture.pdf"))
        comptes.create_recette(cid, _recette())
        noms = zipfile.ZipFile(io.BytesIO(depot.export_dossier_zip(cid))).namelist()
        assert "0_bordereau_de_depot.pdf" in noms, noms
        comptes_zip = sorted(n for n in noms if n.startswith("Comptes/"))
        assert comptes_zip == ["Comptes/compte_campagne_format_cnccfp.xlsx",
                               "Comptes/livre_de_comptes.xlsx",
                               "Comptes/main_courante_annexe8.xlsx"], comptes_zip
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
