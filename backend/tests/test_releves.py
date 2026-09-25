"""Relevés bancaires : lecture des formats et invariants du rapprochement."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import comptes
import maincourante
import releves
from db.session import campaign_session
from db import enums
from database import ROLE_MANDATAIRE
from models import Depense
from _fixture import fresh_campaign, teardown, run_tests

CSV_BANQUE = (
    "Date;Libelle;Debit;Credit\n"
    "08/09/2026;VIR IMPRIMERIE GRENIER;-4 037,21;\n"
    "19/09/2026;CB ERIS RESTAURATION;-1 020,00;\n"
    "12/09/2026;VIR RECU DON;;200,00\n"
    "Solde au 30/09/2026;;;12 345,67\n"
).encode("utf-8")


def _depense(montant, libelle="Tract", jour="2026-09-01"):
    return Depense(date=date.fromisoformat(jour), libelle=libelle, fournisseur="Grenier",
                   montant_ttc=montant, tva=0.0, categorie_cnccfp="A1", statut="Facturé")


def _releve(cid, transactions, libelle="Septembre 2026"):
    return releves.create_releve(cid, releves.ReleveIn(
        libelle=libelle, source="csv",
        transactions=[releves.TransactionIn(**t) for t in transactions]), "gconstant")


def test_lecture_csv_reconnait_sens_et_montants():
    lignes = releves.lire_csv(CSV_BANQUE)
    assert len(lignes) == 3, "la ligne de solde n'est pas une transaction"
    debits = [l for l in lignes if l["sens"] == "debit"]
    assert len(debits) == 2
    assert debits[0]["montant"] == 4037.21
    assert [l for l in lignes if l["sens"] == "credit"][0]["montant"] == 200.0


def test_lecture_texte_pour_le_copier_colle_et_l_ocr():
    texte = """Relevé de compte
08/09/2026  VIR IMPRIMERIE GRENIER        -4 037,21
19 sept. 2026  CB ERIS                     -1 020,00
ligne sans date ni montant
"""
    lignes = releves.lire_texte(texte)
    assert len(lignes) == 2
    assert lignes[1]["date_operation"] == "2026-09-19"
    assert lignes[1]["montant"] == 1020.0


def test_une_transaction_regroupe_plusieurs_depenses():
    """Le cas courant : un virement unique règle plusieurs factures."""
    cid = fresh_campaign()
    try:
        for montant, libelle in ((2904.00, "Lettre Guetté"), (1664.51, "Lettre ouverte")):
            comptes.create_depense(cid, _depense(montant, libelle), "gconstant", ROLE_MANDATAIRE)
        deps = comptes.list_depenses(cid)
        r = _releve(cid, [{"date_operation": "2026-09-22", "libelle": "VIR GRENIER",
                           "montant": 4568.51, "sens": "debit"}])
        transaction = r["transactions"][0]
        assert not transaction["rapprochee"]

        for d in deps:
            releves.imputer(cid, transaction["id"], releves.ImputationIn(depense_id=d["id"]))

        etat = releves.list_releves(cid)[0]["transactions"][0]
        assert etat["rapprochee"]
        assert etat["reste"] == 0.0
        assert len(etat["imputations"]) == 2
    finally:
        teardown(cid)


def test_une_depense_reglee_en_deux_fois():
    """Acompte puis solde : la dépense n'est réglée qu'au dernier versement."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(4037.21, "Courrier"), "gconstant", ROLE_MANDATAIRE)
        dep = comptes.list_depenses(cid)[0]
        r = _releve(cid, [
            {"date_operation": "2026-08-15", "libelle": "ACOMPTE GRENIER", "montant": 1500.0, "sens": "debit"},
            {"date_operation": "2026-09-08", "libelle": "SOLDE GRENIER", "montant": 2537.21, "sens": "debit"},
        ])
        acompte, solde = r["transactions"][0], r["transactions"][1]

        releves.imputer(cid, acompte["id"], releves.ImputationIn(depense_id=dep["id"], montant=1500.0))
        assert releves.depenses_a_rapprocher(cid)[0]["reste"] == 2537.21

        releves.imputer(cid, solde["id"], releves.ImputationIn(depense_id=dep["id"]))
        assert releves.depenses_a_rapprocher(cid) == [], "la dépense est soldée"
    finally:
        teardown(cid)


def test_imputer_au_dela_du_montant_est_refuse():
    """Un rapprochement ne doit jamais faire apparaître plus d'argent qu'il n'en est sorti."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(100.0), "gconstant", ROLE_MANDATAIRE)
        dep = comptes.list_depenses(cid)[0]
        r = _releve(cid, [{"date_operation": "2026-09-10", "libelle": "VIR", "montant": 500.0, "sens": "debit"}])
        t = r["transactions"][0]

        try:
            releves.imputer(cid, t["id"], releves.ImputationIn(depense_id=dep["id"], montant=200.0))
        except HTTPException as e:
            assert e.status_code == 400
            assert "100" in e.detail
        else:
            raise AssertionError("imputer plus que le TTC de la dépense doit être refusé")
    finally:
        teardown(cid)


def test_la_ligne_orpheline_reste_au_releve():
    """Frais bancaires, encaissement de don : la ligne reste, signalée."""
    cid = fresh_campaign()
    try:
        r = _releve(cid, [{"date_operation": "2026-09-04", "libelle": "FRAIS TENUE DE COMPTE",
                           "montant": 4.50, "sens": "debit"}])
        assert r["nb_transactions"] == 1
        assert r["nb_orphelines"] == 1
        assert r["nb_rapprochees"] == 0
    finally:
        teardown(cid)


def test_la_main_courante_montre_facture_et_paiement():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(1020.0, "Buffet", "2026-09-19"), "gconstant", ROLE_MANDATAIRE)
        dep = comptes.list_depenses(cid)[0]
        r = _releve(cid, [{"date_operation": "2026-09-25", "libelle": "CB ERIS RESTAURATION",
                           "montant": 1020.0, "sens": "debit"}])
        releves.imputer(cid, r["transactions"][0]["id"], releves.ImputationIn(depense_id=dep["id"]))

        ligne = [l for l in maincourante.journal(cid) if l["sens"] == "depense"][0]
        assert ligne["date_facture"] == "2026-09-19"
        assert ligne["date_paiement"] == "2026-09-25"
        assert ligne["libelle_releve"] == "CB ERIS RESTAURATION"
        assert ligne["nature"] == "Buffet"
    finally:
        teardown(cid)


def test_retirer_une_imputation_defait_le_reglement():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(300.0), "gconstant", ROLE_MANDATAIRE)
        dep = comptes.list_depenses(cid)[0]
        r = _releve(cid, [{"date_operation": "2026-09-10", "libelle": "VIR", "montant": 300.0, "sens": "debit"}])
        t = releves.imputer(cid, r["transactions"][0]["id"], releves.ImputationIn(depense_id=dep["id"]))
        assert releves.depenses_a_rapprocher(cid) == []

        releves.desimputer(cid, t["imputations"][0]["id"])
        assert releves.depenses_a_rapprocher(cid)[0]["reste"] == 300.0
    finally:
        teardown(cid)


def test_supprimer_un_releve_defait_le_reglement_des_depenses():
    """Sans cela, la dépense reste « payée » en pointant un relevé disparu :
    la trésorerie compte un décaissement sans ligne bancaire derrière."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(1000.0, "Salle"), "gconstant", ROLE_MANDATAIRE)
        dep = comptes.list_depenses(cid)[0]
        r = _releve(cid, [{"date_operation": "2026-09-21", "libelle": "CHQ SALLE",
                           "montant": 1000.0, "sens": "debit"}])
        releves.imputer(cid, r["transactions"][0]["id"], releves.ImputationIn(depense_id=dep["id"]))

        with campaign_session(cid) as s:
            from db.models import Depense as D
            d = s.get(D, dep["id"])
            assert d.rapprochement and d.reglee and d.num_releve_bancaire

        releves.delete_releve(cid, r["id"])

        with campaign_session(cid) as s:
            from db.models import Depense as D
            d = s.get(D, dep["id"])
            assert not d.rapprochement, "plus rien ne la rapproche"
            assert not d.reglee, "plus rien ne la règle"
            assert d.num_releve_bancaire is None, "le relevé n'existe plus"
            assert d.statut != enums.StatutDepense.paye

        assert releves.depenses_a_rapprocher(cid)[0]["reste"] == 1000.0
    finally:
        teardown(cid)


def test_un_encaissement_ne_peut_pas_regler_une_depense():
    """Un crédit est une recette. L'imputer à une dépense fausse le compte."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(500.0), "gconstant", ROLE_MANDATAIRE)
        dep = comptes.list_depenses(cid)[0]
        r = _releve(cid, [{"date_operation": "2026-09-22", "libelle": "VIR RECU DON",
                           "montant": 2000.0, "sens": "credit"}])

        try:
            releves.imputer(cid, r["transactions"][0]["id"],
                            releves.ImputationIn(depense_id=dep["id"], montant=500.0))
        except HTTPException as e:
            assert e.status_code == 400
            assert "encaissement" in e.detail
        else:
            raise AssertionError("imputer un crédit à une dépense doit être refusé")

        assert releves.depenses_a_rapprocher(cid)[0]["reste"] == 500.0
    finally:
        teardown(cid)


def test_le_compteur_a_rapprocher_ignore_les_credits():
    """Sinon il ne tombe jamais à zéro sur un relevé portant un encaissement."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, _depense(300.0), "gconstant", ROLE_MANDATAIRE)
        dep = comptes.list_depenses(cid)[0]
        r = _releve(cid, [
            {"date_operation": "2026-09-10", "libelle": "VIR FOURNISSEUR", "montant": 300.0, "sens": "debit"},
            {"date_operation": "2026-09-12", "libelle": "VIR RECU DON", "montant": 200.0, "sens": "credit"},
        ])
        assert r["nb_rapprochables"] == 1
        assert r["nb_orphelines"] == 1

        debit = [t for t in r["transactions"] if t["sens"] == "debit"][0]
        releves.imputer(cid, debit["id"], releves.ImputationIn(depense_id=dep["id"]))

        etat = releves.list_releves(cid)[0]
        assert etat["nb_orphelines"] == 0, "le crédit ne doit pas empêcher le compteur d'arriver à zéro"
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
