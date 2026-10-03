"""Désigner, à la saisie d'une ligne bancaire, l'écriture qu'elle règle."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import completude
import comptes
import releves
from models import Depense, Recette
from _fixture import fresh_campaign, teardown, run_tests


def _depense(cid, montant=1500.0, libelle="Mission légale"):
    comptes.create_depense(cid, Depense(
        date=date(2026, 9, 23), libelle=libelle, fournisseur="SEROT",
        montant_ttc=montant, tva=0.0, categorie_cnccfp="G1", statut="Facturé"))
    return comptes.list_depenses(cid)[0]["id"]


def _recette(cid, montant=500.0):
    comptes.create_recette(cid, Recette(
        date=date(2026, 9, 8), nom_donateur="MOREAU Sylvie", adresse="1 rue X",
        montant=montant, type="Don"))
    return comptes.list_recettes(cid)[0]["id"]


def _releve(cid, *lignes):
    return releves.create_releve(cid, releves.ReleveIn(
        libelle="Septembre 2026", source="manuel", transactions=list(lignes)), "gaetan")


def _ligne(montant=1500.0, sens="debit", **kw):
    return releves.TransactionIn(date_operation="2026-09-23", libelle="CHQ 4455667",
                                 montant=montant, sens=sens, reference="4455667", **kw)


def test_une_ligne_saisie_regle_la_depense_designee():
    cid = fresh_campaign()
    try:
        did = _depense(cid)
        _releve(cid, _ligne(depense_id=did))
        assert releves.depenses_a_rapprocher(cid) == []
        assert comptes.list_depenses(cid)[0]["statut"] == "Payé"
    finally:
        teardown(cid)


def test_un_credit_saisi_alimente_la_recette_designee():
    cid = fresh_campaign()
    try:
        rid = _recette(cid)
        _releve(cid, _ligne(montant=500.0, sens="credit", recette_id=rid))
        assert releves.recettes_a_rapprocher(cid) == []
    finally:
        teardown(cid)


def test_un_credit_ne_peut_pas_regler_une_depense():
    cid = fresh_campaign()
    try:
        did = _depense(cid)
        raised = False
        try:
            _releve(cid, _ligne(sens="credit", depense_id=did))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400 and "encaissement" in e.detail
        assert raised
    finally:
        teardown(cid)


def test_un_debit_ne_peut_pas_alimenter_une_recette():
    cid = fresh_campaign()
    try:
        rid = _recette(cid)
        raised = False
        try:
            _releve(cid, _ligne(sens="debit", recette_id=rid))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400 and "décaissement" in e.detail
        assert raised
    finally:
        teardown(cid)


def test_une_ligne_plus_petite_laisse_la_depense_ouverte():
    """Un acompte ne solde pas la facture."""
    cid = fresh_campaign()
    try:
        did = _depense(cid, montant=1500.0)
        _releve(cid, _ligne(montant=500.0, depense_id=did))
        restant = releves.depenses_a_rapprocher(cid)
        assert [d["reste"] for d in restant] == [1000.0], restant
    finally:
        teardown(cid)


def test_une_ligne_plus_grosse_n_impute_que_le_du():
    """La ligne couvre la facture sans jamais imputer plus qu'elle ne doit."""
    cid = fresh_campaign()
    try:
        did = _depense(cid, montant=1500.0)
        r = _releve(cid, _ligne(montant=2000.0, depense_id=did))
        t = r["transactions"][0]
        assert t["montant_impute"] == 1500.0 and t["reste"] == 500.0, t
        assert releves.depenses_a_rapprocher(cid) == []
    finally:
        teardown(cid)


def test_ajout_sur_un_releve_existant_impute_aussi():
    cid = fresh_campaign()
    try:
        did = _depense(cid)
        r = _releve(cid, _ligne(montant=10.0, libelle=None) if False else
                    releves.TransactionIn(date_operation="2026-09-01",
                                          libelle="Frais", montant=10.0, sens="debit"))
        releves.ajouter_transaction(cid, r["id"], _ligne(depense_id=did))
        assert releves.depenses_a_rapprocher(cid) == []
    finally:
        teardown(cid)


def test_sans_designation_la_ligne_reste_libre():
    """Saisir une ligne sans la rattacher doit rester possible."""
    cid = fresh_campaign()
    try:
        did = _depense(cid)
        _releve(cid, _ligne())
        assert [d["id"] for d in releves.depenses_a_rapprocher(cid)] == [did]
    finally:
        teardown(cid)


def test_le_reste_a_faire_baisse_a_la_saisie():
    cid = fresh_campaign()
    try:
        did = _depense(cid)
        avant = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["rapprochement"]
        assert avant["remplis"] == 0, avant
        _releve(cid, _ligne(depense_id=did))
        apres = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["rapprochement"]
        assert apres["complet"], apres
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
