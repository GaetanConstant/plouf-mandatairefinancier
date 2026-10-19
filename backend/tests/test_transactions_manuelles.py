"""Saisie manuelle des transactions, et le relevé comme pièce du dossier."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import completude
import comptes
import releves
from models import Depense
from _fixture import fresh_campaign, teardown, run_tests


def _releve_vide(cid, libelle="Septembre 2026", fichier=None):
    return releves.create_releve(cid, releves.ReleveIn(
        libelle=libelle, source="manuel", fichier=fichier,
        transactions=[releves.TransactionIn(
            date_operation="2026-09-01", libelle="Report", montant=10.0, sens="debit")]),
        "gaetan")


def _ligne(date_op="2026-09-12", libelle="CHQ 1234567", montant=620.0,
           sens="debit", reference="1234567"):
    return releves.TransactionIn(date_operation=date_op, libelle=libelle,
                                 montant=montant, sens=sens, reference=reference)


def _section(cid, cle="releves"):
    return {s["cle"]: s for s in completude.evaluer(cid)["sections"]}[cle]


def test_ajouter_une_ligne_a_la_main():
    """Toutes les banques ne donnent pas un export exploitable."""
    cid = fresh_campaign()
    try:
        r = _releve_vide(cid)
        t = releves.ajouter_transaction(cid, r["id"], _ligne())
        assert t["libelle"] == "CHQ 1234567" and t["montant"] == 620.0, t
        assert t["reference"] == "1234567", t
        releve = releves.list_releves(cid)[0]
        assert releve["nb_transactions"] == 2, releve
    finally:
        teardown(cid)


def test_les_bornes_du_releve_suivent_les_lignes():
    cid = fresh_campaign()
    try:
        r = _releve_vide(cid)
        assert releves.list_releves(cid)[0]["date_fin"] == "2026-09-01"
        releves.ajouter_transaction(cid, r["id"], _ligne(date_op="2026-09-28"))
        assert releves.list_releves(cid)[0]["date_fin"] == "2026-09-28"
    finally:
        teardown(cid)


def test_une_ligne_saisie_se_rapproche_comme_une_autre():
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 9, 10), libelle="Salle", fournisseur="Mairie",
            montant_ttc=620.0, tva=0.0, categorie_cnccfp="B1", statut="Facturé"))
        did = comptes.list_depenses(cid)[0]["id"]
        r = _releve_vide(cid)
        t = releves.ajouter_transaction(cid, r["id"], _ligne())
        res = releves.imputer(cid, t["id"], releves.ImputationIn(depense_id=did))
        assert res["rapprochee"] is True, res
    finally:
        teardown(cid)


def test_retirer_une_ligne_delie_la_depense():
    """Sinon la dépense resterait payée en pointant une ligne disparue."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 9, 10), libelle="Salle", fournisseur="Mairie",
            montant_ttc=620.0, tva=0.0, categorie_cnccfp="B1", statut="Facturé"))
        did = comptes.list_depenses(cid)[0]["id"]
        r = _releve_vide(cid)
        t = releves.ajouter_transaction(cid, r["id"], _ligne())
        releves.imputer(cid, t["id"], releves.ImputationIn(depense_id=did))
        assert releves.depenses_a_rapprocher(cid) == []

        releves.supprimer_transaction(cid, t["id"])
        assert [d["id"] for d in releves.depenses_a_rapprocher(cid)] == [did]
    finally:
        teardown(cid)


def test_un_montant_negatif_est_refuse():
    """Le sens dit débit ou crédit ; le montant reste positif."""
    cid = fresh_campaign()
    try:
        r = _releve_vide(cid)
        raised = False
        try:
            releves.ajouter_transaction(cid, r["id"], _ligne(montant=-50.0))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
