"""Cycle de validation : ce qui entre dans le compte, et ce qui n'y entre pas."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import comptes
import conformite
import evenements
import maincourante
import validation
from database import ROLE_DIRECTION, ROLE_EQUIPE, ROLE_EXPERT, ROLE_MANDATAIRE
from models import Depense
from _fixture import fresh_campaign, teardown, run_tests


def _depense(montant=100.0):
    return Depense(date=date(2026, 1, 10), libelle="Tract", fournisseur="Imprimerie",
                   montant_ttc=montant, tva=0.0, categorie_cnccfp="A1", statut="Payé")


def test_depense_de_l_equipe_hors_du_compte_avant_validation():
    """L'invariant central : un militant ne déplace pas un chiffre légal."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(500.0), "militant", ROLE_EQUIPE)
        assert comptes.compute_stats(cid)["total_depenses"] == 0.0
        assert comptes.list_depenses(cid) == []
    finally:
        teardown(cid)


def test_la_validation_fait_entrer_la_depense_dans_le_compte():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(500.0), "militant", ROLE_EQUIPE)
        file = validation.file_attente(cid)
        assert file["nb_elements"] == 1
        element = file["elements"][0]
        assert element["cree_par"] == "militant"

        validation.valider(cid, element["entite"], element["id"], "gconstant")
        assert comptes.compute_stats(cid)["total_depenses"] == 500.0
        assert validation.file_attente(cid)["nb_elements"] == 0
    finally:
        teardown(cid)


def test_depense_du_mandataire_directement_au_compte():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(300.0), "gconstant", ROLE_MANDATAIRE)
        assert comptes.compute_stats(cid)["total_depenses"] == 300.0
        assert validation.file_attente(cid)["nb_elements"] == 0
    finally:
        teardown(cid)


def test_refus_ne_supprime_pas_et_laisse_resoumettre():
    """Une erreur d'arbitrage ne doit pas détruire une pièce comptable."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(200.0), "militant", ROLE_EQUIPE)
        element = validation.file_attente(cid)["elements"][0]

        validation.refuser(cid, element["entite"], element["id"], "gconstant", "Facture illisible")
        mien = validation.mes_soumissions(cid, "militant")
        assert len(mien) == 1
        assert mien[0]["statut"] == "refuse"
        assert mien[0]["motif_refus"] == "Facture illisible"
        assert comptes.compute_stats(cid)["total_depenses"] == 0.0

        validation.resoumettre(cid, element["entite"], element["id"], "militant")
        assert validation.file_attente(cid)["nb_elements"] == 1
    finally:
        teardown(cid)


def test_resoumettre_le_depot_d_un_autre_est_refuse():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(), "militant", ROLE_EQUIPE)
        element = validation.file_attente(cid)["elements"][0]
        validation.refuser(cid, element["entite"], element["id"], "gconstant", "non")
        try:
            validation.resoumettre(cid, element["entite"], element["id"], "autre")
        except HTTPException as e:
            assert e.status_code == 403
        else:
            raise AssertionError("un contributeur ne resoumet que ses propres dépôts")
    finally:
        teardown(cid)


def test_une_soumission_en_attente_reste_hors_des_controles_et_du_journal():
    """Conformité et main courante ne jugent que le compte réel."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(9_999_999.0), "militant", ROLE_EQUIPE)
        assert conformite.run_checks(cid)["compteurs"]["bloquant"] == 0
        assert maincourante.journal(cid) == [] or all(
            l.get("libelle") != "Tract" for l in maincourante.journal(cid))
    finally:
        teardown(cid)


def test_evenement_de_l_equipe_absent_de_la_liste_avant_validation():
    cid = fresh_campaign()
    try:
        evenements.create_evenement(cid, evenements.EvenementIn(
            titre="Porte à porte", type="porte_a_porte", date_debut="2026-05-02"),
            "militant", ROLE_EQUIPE)
        assert evenements.list_evenements(cid) == []
        assert validation.file_attente(cid)["nb_elements"] == 1
    finally:
        teardown(cid)


def test_demande_de_piece_de_l_expert_compte_dans_la_file():
    cid = fresh_campaign()
    try:
        validation.create_demande(cid, validation.DemandePieceIn(
            message="Merci de fournir le relevé bancaire de septembre."), "esserot")
        file = validation.file_attente(cid)
        assert file["nb_demandes_pieces"] == 1
        assert file["total"] == 1
    finally:
        teardown(cid)


def test_la_direction_ne_voit_pas_l_identite_des_donateurs():
    """Un don politique est une opinion : la direction voit la règle enfreinte,
    pas qui a donné."""
    from models import Recette as RecetteIn

    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, RecetteIn(
            date=date(2026, 5, 4), nom_donateur="MARTIN Claire", adresse="2 rue Y",
            montant=200.0, type="Don"), "gconstant", ROLE_MANDATAIRE)

        nomme = maincourante.journal(cid, voir_donateurs=True)
        masque = maincourante.journal(cid, voir_donateurs=False)
        assert any(l.get("tiers") == "MARTIN Claire" for l in nomme)
        assert all(l.get("tiers") != "MARTIN Claire" for l in masque)
    finally:
        teardown(cid)


def test_le_masquage_conserve_l_alerte_et_sa_cible():
    """Masquer le nom ne doit pas rendre l'alerte inexploitable."""
    from models import Recette as RecetteIn

    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, RecetteIn(
            date=date(2026, 5, 4), nom_donateur="DURAND Paul", adresse="",
            montant=200.0, type="Don"), "gconstant", ROLE_MANDATAIRE)

        masque = conformite.run_checks(cid, voir_donateurs=False)
        messages = " ".join(a["message"] for a in masque["alertes"])
        assert "DURAND" not in messages
        # L'alerte garde l'entité et son identifiant : elle reste actionnable.
        assert any(a["entite"] == "recette" and a["entite_id"] for a in masque["alertes"])
    finally:
        teardown(cid)


def test_la_direction_depose_une_piece_sans_toucher_aux_montants():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(400.0), "gconstant", ROLE_MANDATAIRE)
        dep = comptes.list_depenses(cid)[0]
        assert dep["justificatif_path"] is None

        comptes.ajouter_piece(cid, dep["id"], comptes.PieceIn(
            fichier="/data/uploads/facture_direction.pdf"), "adavid", ROLE_DIRECTION)

        apres = comptes.list_depenses(cid)[0]
        assert apres["montant_ttc"] == 400.0, "le montant ne bouge pas"
        # La pièce est en attente : elle n'apparaît pas encore au dossier.
        assert apres["justificatif_path"] is None
        file = validation.file_attente(cid)
        assert file["nb_elements"] == 1
        assert file["elements"][0]["cree_par"] == "adavid"

        element = file["elements"][0]
        validation.valider(cid, element["entite"], element["id"], "gconstant")
        assert comptes.list_depenses(cid)[0]["justificatif_path"] == "facture_direction.pdf"
    finally:
        teardown(cid)


def test_la_direction_ne_remplace_pas_une_piece_deja_validee():
    """Remplacer une pièce du compte est une décision du mandataire."""
    cid = fresh_campaign()
    try:
        d = _depense(400.0)
        d.justificatif_path = "/data/uploads/facture_initiale.pdf"
        comptes.create_depense(cid, d, "gconstant", ROLE_MANDATAIRE)
        dep = comptes.list_depenses(cid)[0]

        try:
            comptes.ajouter_piece(cid, dep["id"], comptes.PieceIn(
                fichier="/data/uploads/autre.pdf"), "adavid", ROLE_DIRECTION)
        except HTTPException as e:
            assert e.status_code == 409
        else:
            raise AssertionError("le dépôt aurait dû être refusé")

        assert comptes.list_depenses(cid)[0]["justificatif_path"] == "facture_initiale.pdf"
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
