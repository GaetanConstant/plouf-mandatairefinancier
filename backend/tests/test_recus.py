"""Tests des reçus-dons : numérotation séquentielle, idempotence, épuisement,
éligibilité à l'avantage fiscal."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException
from sqlalchemy import select

import comptes
import recus
from models import Recette
from db.session import campaign_session
from db.models import Recette as ORMRecette
from db import enums
from _fixture import fresh_campaign, teardown, run_tests


def _add_don(cid, montant=100.0, nom="DUPONT Jean", mode=None):
    comptes.create_recette(cid, Recette(date=date(2026, 1, 10), nom_donateur=nom,
                                        adresse="1 rue X", montant=montant, type="Don"))
    with campaign_session(cid) as s:
        r = s.scalars(select(ORMRecette).order_by(ORMRecette.id.desc())).first()
        if mode is not None:
            r.mode = mode
        return r.id


def test_numerotation_sequentielle():
    cid = fresh_campaign()
    try:
        recus.create_carnet(cid, "CARN-A", 1, 5)
        r1 = _add_don(cid, nom="A A"); r2 = _add_don(cid, nom="B B")
        assert recus.issue_recu(cid, r1)["numero_formule"] == 1
        assert recus.issue_recu(cid, r2)["numero_formule"] == 2
    finally:
        teardown(cid)


def test_idempotent_par_recette():
    cid = fresh_campaign()
    try:
        recus.create_carnet(cid, "CARN-A", 1, 5)
        r = _add_don(cid)
        first = recus.issue_recu(cid, r)
        again = recus.issue_recu(cid, r)
        assert again["numero_formule"] == first["numero_formule"]
        assert again["message"] == "Reçu déjà délivré"
    finally:
        teardown(cid)


def test_carnet_epuise_rejete():
    cid = fresh_campaign()
    try:
        recus.create_carnet(cid, "CARN-A", 1, 2)  # 2 formules
        ids = [_add_don(cid, nom=f"D{i}") for i in range(3)]
        recus.issue_recu(cid, ids[0]); recus.issue_recu(cid, ids[1])
        raised = False
        try:
            recus.issue_recu(cid, ids[2])
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised, "le carnet épuisé aurait dû rejeter le 3e reçu"
    finally:
        teardown(cid)


def test_carnet_stats_delivres_annules_restants():
    cid = fresh_campaign()
    try:
        cid_carnet = recus.create_carnet(cid, "CARN-A", 1, 3)["id"]
        ids = [_add_don(cid, nom=f"D{i}") for i in range(2)]
        recu1 = recus.issue_recu(cid, ids[0])["id"]
        recus.issue_recu(cid, ids[1])
        recus.annuler_recu(cid, recu1)
        c = next(x for x in recus.list_carnets(cid) if x["id"] == cid_carnet)
        assert (c["nb_total"], c["nb_delivres"], c["nb_annules"], c["nb_restants"]) == (3, 1, 1, 1)
    finally:
        teardown(cid)


def test_avantage_fiscal_especes_exclu():
    cid = fresh_campaign()
    try:
        recus.create_carnet(cid, "CARN-A", 1, 5)
        r_esp = _add_don(cid, nom="Esp", mode=enums.ModePaiement.especes)
        r_chq = _add_don(cid, nom="Chq", mode=enums.ModePaiement.cheque)
        recus.issue_recu(cid, r_esp); recus.issue_recu(cid, r_chq)
        m = {x["nom_donateur"]: x["avantage_fiscal_eligible"] for x in recus.list_recus(cid)}
        assert m["Esp"] is False     # espèces → pas d'avantage fiscal
        assert m["Chq"] is True
    finally:
        teardown(cid)


def test_recu_seulement_pour_dons():
    cid = fresh_campaign()
    try:
        recus.create_carnet(cid, "CARN-A", 1, 5)
        comptes.create_recette(cid, Recette(date=date(2026, 1, 10), nom_donateur="Banque",
                                            adresse="", montant=5000, type="Pret"))
        with campaign_session(cid) as s:
            pret_id = s.scalars(__import__("sqlalchemy").select(ORMRecette)).first().id
        raised = False
        try:
            recus.issue_recu(cid, pret_id)
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised, "un prêt ne doit pas donner lieu à un reçu-don"
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
