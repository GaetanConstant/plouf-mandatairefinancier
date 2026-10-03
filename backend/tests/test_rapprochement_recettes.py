"""Rapprochement bancaire des recettes, et son exigence dans le reste à faire."""

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


def _releve(cid, lignes):
    """Importe un relevé. `lignes` : (libellé, montant, sens)."""
    return releves.create_releve(cid, releves.ReleveIn(
        libelle="Relevé septembre", source="csv",
        transactions=[releves.TransactionIn(date_operation="2026-09-08", libelle=lib,
                                            montant=m, sens=sens)
                      for lib, m, sens in lignes]), "gaetan")


def _recette(cid, montant=500.0, nom="MOREAU Sylvie"):
    comptes.create_recette(cid, Recette(
        date=date(2026, 9, 8), nom_donateur=nom, adresse="1 rue X",
        montant=montant, type="Don"))
    return comptes.list_recettes(cid)[0]["id"]


def _section(cid, cle="rapprochement"):
    return {s["cle"]: s for s in completude.evaluer(cid)["sections"]}.get(cle)


def test_un_credit_alimente_une_recette():
    cid = fresh_campaign()
    try:
        rid = _recette(cid, 500.0)
        rel = _releve(cid, [("VIR DON MOREAU", 500.0, "credit")])
        tid = rel["transactions"][0]["id"]
        res = releves.imputer_recette(cid, tid, releves.ImputationRecetteIn(recette_id=rid))
        assert res["rapprochee"] is True, res
        assert comptes.list_recettes(cid)[0]["id"] == rid
    finally:
        teardown(cid)


def test_un_debit_ne_peut_pas_alimenter_une_recette():
    cid = fresh_campaign()
    try:
        rid = _recette(cid)
        rel = _releve(cid, [("PRLV LOYER", 120.0, "debit")])
        tid = rel["transactions"][0]["id"]
        raised = False
        try:
            releves.imputer_recette(cid, tid, releves.ImputationRecetteIn(recette_id=rid))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400 and "décaissement" in e.detail
        assert raised
    finally:
        teardown(cid)


def test_imputation_plafonnee_au_montant_de_la_recette():
    cid = fresh_campaign()
    try:
        rid = _recette(cid, 300.0)
        rel = _releve(cid, [("REMISE CHEQUES", 1000.0, "credit")])
        tid = rel["transactions"][0]["id"]
        raised = False
        try:
            releves.imputer_recette(cid, tid,
                                    releves.ImputationRecetteIn(recette_id=rid, montant=500.0))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised
    finally:
        teardown(cid)


def test_une_remise_couvre_plusieurs_dons():
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, Recette(date=date(2026, 9, 8), nom_donateur="A A",
                                            adresse="x", montant=200.0, type="Don"))
        comptes.create_recette(cid, Recette(date=date(2026, 9, 8), nom_donateur="B B",
                                            adresse="y", montant=300.0, type="Don"))
        ids = [r["id"] for r in comptes.list_recettes(cid)]
        rel = _releve(cid, [("REMISE CHEQUES", 500.0, "credit")])
        tid = rel["transactions"][0]["id"]
        for rid in ids:
            res = releves.imputer_recette(cid, tid, releves.ImputationRecetteIn(recette_id=rid))
        assert res["rapprochee"] is True and res["reste"] == 0.0, res
        assert releves.recettes_a_rapprocher(cid) == []
    finally:
        teardown(cid)


def test_recette_non_rapprochee_bloque_le_depot():
    cid = fresh_campaign()
    try:
        _recette(cid, 500.0)
        _releve(cid, [("VIR DON MOREAU", 500.0, "credit")])
        sec = _section(cid)
        assert sec is not None and not sec["complet"], sec
        assert any("Recette" in m for m in sec["manquants"]), sec["manquants"]
    finally:
        teardown(cid)


def test_section_absente_tant_qu_aucun_releve():
    """Sans relevé importé, la section « Relevés bancaires » le dit déjà."""
    cid = fresh_campaign()
    try:
        _recette(cid)
        assert _section(cid) is None
    finally:
        teardown(cid)


def test_concours_en_nature_exclu_du_rapprochement():
    """Une prestation donnée ne passe pas par le compte : elle n'a rien à rapprocher."""
    cid = fresh_campaign()
    try:
        comptes.create_depense(cid, Depense(
            date=date(2026, 9, 1), libelle="Salle prêtée", fournisseur="Mairie",
            montant_ttc=300.0, tva=0.0, categorie_cnccfp="B1", statut="Payé",
            is_nature=True))
        _releve(cid, [("VIR", 10.0, "credit")])
        assert _section(cid)["requis"] == 0, _section(cid)
    finally:
        teardown(cid)


def test_supprimer_le_releve_delie_la_recette():
    cid = fresh_campaign()
    try:
        rid = _recette(cid, 500.0)
        rel = _releve(cid, [("VIR DON", 500.0, "credit")])
        releves.imputer_recette(cid, rel["transactions"][0]["id"],
                                releves.ImputationRecetteIn(recette_id=rid))
        assert releves.recettes_a_rapprocher(cid) == []
        releves.delete_releve(cid, rel["id"])
        # La recette redevient à rapprocher : sinon elle pointerait un relevé disparu.
        assert [r["id"] for r in releves.recettes_a_rapprocher(cid)] == [rid]
    finally:
        teardown(cid)


def test_desimputer_remet_la_recette_a_rapprocher():
    cid = fresh_campaign()
    try:
        rid = _recette(cid, 500.0)
        rel = _releve(cid, [("VIR DON", 500.0, "credit")])
        res = releves.imputer_recette(cid, rel["transactions"][0]["id"],
                                      releves.ImputationRecetteIn(recette_id=rid))
        releves.desimputer_recette(cid, res["imputations"][0]["id"])
        assert [r["id"] for r in releves.recettes_a_rapprocher(cid)] == [rid]
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
