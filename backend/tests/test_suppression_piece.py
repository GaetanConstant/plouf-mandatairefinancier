"""Suppression d'une pièce : les rattachements doivent partir avec elle."""

import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import comptes
import depot
import evenements
from database import UPLOADS_DIR
from db.models import Document
from db.session import campaign_session
from models import Depense, Recette
from _fixture import fresh_campaign, teardown, run_tests


def _fichier(nom: str) -> str:
    chemin = Path(UPLOADS_DIR) / nom
    chemin.write_bytes(b"%PDF-1.4 piece de test")
    return nom


def _depense_avec_piece(cid, fichier):
    comptes.create_depense(cid, Depense(
        date=date(2026, 9, 1), libelle="Impression", fournisseur="Imprimeur",
        montant_ttc=500.0, tva=0.0, categorie_cnccfp="A1", statut="Payé",
        justificatif_path=fichier))
    return comptes.list_depenses(cid)[0]["id"]


def test_supprimer_une_piece_detache_la_depense():
    cid = fresh_campaign()
    nom = _fichier("test_facture_a.pdf")
    try:
        did = _depense_avec_piece(cid, nom)
        assert comptes.list_depenses(cid)[0]["justificatif_path"] == nom
        res = depot.supprimer_piece(cid, nom, [cid])
        assert res["pieces_retirees"] == 1 and res["fichier_efface"] is True, res
        assert comptes.list_depenses(cid)[0]["justificatif_path"] is None
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid)


def test_supprimer_une_piece_detache_l_evenement():
    """Le cas demandé : la pièce ne doit plus figurer sur l'événement."""
    cid = fresh_campaign()
    nom = _fichier("test_photo_b.jpg")
    try:
        ev = evenements.create_evenement(cid, evenements.EvenementIn(
            titre="Meeting", type="meeting", date_debut="2026-09-05"))["id"]
        evenements.link_document(cid, ev, evenements.DocumentEvenementIn(
            fichier=nom, type_piece="photo"), auteur="gaetan", role="mandataire")
        assert len(evenements.list_documents_evenement(cid, ev)) == 1

        depot.supprimer_piece(cid, nom, [cid])
        assert evenements.list_documents_evenement(cid, ev) == []
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid)


def test_la_piece_disparait_du_dossier_de_depot():
    cid = fresh_campaign()
    nom = _fichier("test_facture_c.pdf")
    try:
        _depense_avec_piece(cid, nom)
        assert len(depot.get_depot(cid)["pieces_A"]) == 1
        depot.supprimer_piece(cid, nom, [cid])
        assert depot.get_depot(cid)["pieces_A"] == []
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid)


def test_un_fantome_sans_fichier_reste_supprimable():
    """Sans ça, une pièce dont le fichier a disparu bloque le dépôt sans issue."""
    cid = fresh_campaign()
    nom = _fichier("test_fantome_d.pdf")
    try:
        _depense_avec_piece(cid, nom)
        (Path(UPLOADS_DIR) / nom).unlink()           # le fichier s'évapore
        assert depot.pieces_sans_fichier(cid) == [nom]

        res = depot.supprimer_piece(cid, nom, [cid])
        assert res["pieces_retirees"] == 1 and res["fichier_efface"] is False, res
        assert depot.pieces_sans_fichier(cid) == []
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid)


def test_le_fichier_survit_s_il_sert_a_une_autre_campagne():
    """`uploads` est commun : un testeur ne doit pas trouer le dossier d'un autre."""
    cid_a, cid_b = fresh_campaign(), fresh_campaign()
    nom = _fichier("test_partage_e.pdf")
    try:
        _depense_avec_piece(cid_a, nom)
        _depense_avec_piece(cid_b, nom)
        res = depot.supprimer_piece(cid_a, nom, [cid_a, cid_b])
        assert res["conserve_pour_autre_campagne"] is True, res
        assert res["fichier_efface"] is False
        assert (Path(UPLOADS_DIR) / nom).is_file()
        # La campagne B garde sa pièce intacte.
        assert comptes.list_depenses(cid_b)[0]["justificatif_path"] == nom
        assert comptes.list_depenses(cid_a)[0]["justificatif_path"] is None
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid_a); teardown(cid_b)


def test_la_depense_retourne_dans_le_reste_a_faire():
    """Supprimer le justificatif doit rouvrir la ligne, pas la faire oublier."""
    import completude
    cid = fresh_campaign()
    nom = _fichier("test_facture_f.pdf")
    try:
        _depense_avec_piece(cid, nom)
        sec = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}
        assert sec["justificatifs_depenses"]["complet"]
        depot.supprimer_piece(cid, nom, [cid])
        sec = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}
        assert not sec["justificatifs_depenses"]["complet"]
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
