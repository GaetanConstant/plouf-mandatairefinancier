"""Dépenses avancées par une personne, et ce que la campagne lui doit."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import comptes
import releves
from models import Depense
from _fixture import fresh_campaign, teardown, run_tests


def _depense(cid, libelle="Essence", montant=40.0, fournisseur="Station Total",
             avance_par=None):
    comptes.create_depense(cid, Depense(
        date=date(2026, 9, 20), libelle=libelle, fournisseur=fournisseur,
        montant_ttc=montant, tva=0.0, categorie_cnccfp="D1", statut="Facturé",
        avance_par=avance_par))
    return comptes.list_depenses(cid)[0]["id"]


def test_le_fournisseur_reste_le_vrai_fournisseur():
    """Le colleur qui paie l'essence ne devient pas la station-service."""
    cid = fresh_campaign()
    try:
        _depense(cid, avance_par="DUPONT Marc")
        d = comptes.list_depenses(cid)[0]
        assert d["fournisseur"] == "Station Total", d
        assert d["avance_par"] == "DUPONT Marc", d
    finally:
        teardown(cid)


def test_les_avances_se_regroupent_par_personne():
    cid = fresh_campaign()
    try:
        _depense(cid, "Essence", 40.0, avance_par="DUPONT Marc")
        _depense(cid, "Colle", 18.50, fournisseur="Papeterie", avance_par="DUPONT Marc")
        _depense(cid, "Péage", 12.0, fournisseur="APRR", avance_par="MARTIN Léa")
        avances = comptes.avances_a_rembourser(cid)
        assert [a["personne"] for a in avances] == ["DUPONT Marc", "MARTIN Léa"], avances
        assert avances[0]["total"] == 58.50 and len(avances[0]["lignes"]) == 2, avances[0]
    finally:
        teardown(cid)


def test_une_depense_sans_avance_n_y_figure_pas():
    cid = fresh_campaign()
    try:
        _depense(cid, "Impression", 900.0, fournisseur="Imprimeur")
        assert comptes.avances_a_rembourser(cid) == []
    finally:
        teardown(cid)


def test_le_remboursement_se_constate_au_relevé():
    """C'est le rapprochement qui atteste du remboursement, pas une case."""
    cid = fresh_campaign()
    try:
        did = _depense(cid, "Essence", 40.0, avance_par="DUPONT Marc")
        assert comptes.avances_a_rembourser(cid)[0]["total"] == 40.0

        r = releves.create_releve(cid, releves.ReleveIn(
            libelle="Septembre", source="manuel",
            transactions=[releves.TransactionIn(
                date_operation="2026-09-28", libelle="VIR DUPONT MARC",
                montant=40.0, sens="debit", depense_id=did)]), "gaetan")
        assert r["transactions"][0]["rapprochee"] is True
        assert comptes.avances_a_rembourser(cid) == []
    finally:
        teardown(cid)


def test_la_modification_met_a_jour_l_avance():
    cid = fresh_campaign()
    try:
        did = _depense(cid, avance_par="DUPONT Marc")
        comptes.update_depense(cid, did, Depense(
            date=date(2026, 9, 20), libelle="Essence", fournisseur="Station Total",
            montant_ttc=40.0, tva=0.0, categorie_cnccfp="D1", statut="Facturé",
            avance_par="MARTIN Léa"))
        assert comptes.avances_a_rembourser(cid)[0]["personne"] == "MARTIN Léa"
    finally:
        teardown(cid)


def test_un_champ_vide_ne_cree_pas_d_avance():
    cid = fresh_campaign()
    try:
        _depense(cid, avance_par="   ")
        assert comptes.list_depenses(cid)[0]["avance_par"] is None
        assert comptes.avances_a_rembourser(cid) == []
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
