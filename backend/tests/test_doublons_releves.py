"""Doublons de lignes bancaires : un export cumulatif ne doit rien compter deux fois."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import comptes
import releves
from database import ROLE_MANDATAIRE
from models import Depense
from _fixture import fresh_campaign, teardown, run_tests

GRENIER = {"date_operation": "2026-10-19", "libelle": "VIR INSTANTANE IMPRIMERIE GRENIER",
           "montant": 3985.80, "sens": "debit"}
ERIS = {"date_operation": "2026-10-19", "libelle": "VIR INSTANTANE ERIS BUFFET",
        "montant": 1020.00, "sens": "debit"}
COTISATION = {"date_operation": "2026-10-19", "libelle": "COTISATION ADISPO",
              "montant": 21.00, "sens": "debit"}
LOUPIOTE = {"date_operation": "2026-10-19", "libelle": "VIR INSTANTANE LA LOUPIOTE",
            "montant": 22.32, "sens": "debit"}


def _releve(cid, transactions, libelle):
    return releves.create_releve(cid, releves.ReleveIn(
        libelle=libelle, source="csv",
        transactions=[releves.TransactionIn(**t) for t in transactions]), "gconstant")


def _doublons(cid):
    return {t["libelle"]: t["doublon_de"]
            for r in releves.list_releves(cid) for t in r["transactions"] if t["doublon_de"]}


def test_l_export_du_jour_telecharge_deux_fois():
    """Le cas vu en prod le 19/10 : le second export reprend les lignes du premier."""
    cid = fresh_campaign()
    try:
        premier = _releve(cid, [GRENIER, ERIS, COTISATION], "Jour 9h13")
        _releve(cid, [LOUPIOTE, GRENIER, ERIS, COTISATION], "Jour 9h31")

        doublons = _doublons(cid)
        assert set(doublons) == {GRENIER["libelle"], ERIS["libelle"], COTISATION["libelle"]}
        ids_premier = {t["id"] for t in premier["transactions"]}
        assert all(d["id"] in ids_premier for d in doublons.values()), \
            "c'est la seconde copie qu'on propose de retirer"
    finally:
        teardown(cid)


def test_la_copie_rapprochee_est_celle_qu_on_garde():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 10, 1), libelle="Tracts", fournisseur="Grenier",
            montant_ttc=3985.80, tva=0.0, categorie_cnccfp="A1", statut="Facturé"),
            "gconstant", ROLE_MANDATAIRE)
        depense = comptes.list_depenses(cid)[0]
        _releve(cid, [GRENIER], "Jour 9h13")
        second = _releve(cid, [GRENIER], "Jour 9h31")
        releves.imputer(cid, second["transactions"][0]["id"],
                        releves.ImputationIn(depense_id=depense["id"]))

        doublons = [t for r in releves.list_releves(cid) for t in r["transactions"]
                    if t["doublon_de"]]
        assert len(doublons) == 1
        assert not doublons[0]["rapprochee"]
        assert doublons[0]["doublon_de"]["id"] == second["transactions"][0]["id"]
    finally:
        teardown(cid)


def test_deux_operations_identiques_du_meme_import_ne_sont_pas_des_doublons():
    """Deux cotisations le même jour, dans le même fichier : deux vraies opérations."""
    cid = fresh_campaign()
    try:
        _releve(cid, [COTISATION, COTISATION], "Octobre")
        assert _doublons(cid) == {}
    finally:
        teardown(cid)


def test_l_historique_reprend_l_operation_a_une_autre_date():
    """L'export d'historique peut dater l'opération du jour de comptabilisation."""
    cid = fresh_campaign()
    try:
        _releve(cid, [GRENIER], "Jour")
        _releve(cid, [{**GRENIER, "date_operation": "2026-10-21"}], "Historique")
        assert GRENIER["libelle"] in _doublons(cid)

        _releve(cid, [{**ERIS, "date_operation": "2026-09-01"}], "Septembre")
        _releve(cid, [ERIS], "Jour")
        assert ERIS["libelle"] not in _doublons(cid), "six semaines d'écart : deux paiements"
    finally:
        teardown(cid)


def test_l_apercu_d_import_signale_les_lignes_deja_presentes():
    cid = fresh_campaign()
    try:
        _releve(cid, [GRENIER, COTISATION], "Jour 9h13")
        lues = releves.signaler_deja_presentes(
            cid, [dict(l) for l in (GRENIER, COTISATION, COTISATION, LOUPIOTE)])
        presentes = [l for l in lues if l["deja_present"]]
        assert len(presentes) == 2, "la seconde cotisation du fichier est nouvelle"
        assert lues[2]["deja_present"] is None
        assert lues[3]["deja_present"] is None
    finally:
        teardown(cid)


def test_supprimer_le_doublon_le_fait_disparaitre():
    cid = fresh_campaign()
    try:
        _releve(cid, [GRENIER], "Jour 9h13")
        second = _releve(cid, [GRENIER], "Jour 9h31")
        releves.supprimer_transaction(cid, second["transactions"][0]["id"])
        assert _doublons(cid) == {}
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
