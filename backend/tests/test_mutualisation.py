"""Tests mutualisation : Σ pourcentages = 100 % et calcul de notre quote-part."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import mutualisation
from _fixture import fresh_campaign, teardown, run_tests


def test_somme_pourcentages_doit_faire_100():
    cid = fresh_campaign()
    try:
        pid = mutualisation.create_partie(cid, mutualisation.PartieExterneIn(nom="Amard"))["id"]
        payload = mutualisation.MutualiseeIn(
            objet="Local", montant_total_ttc=1000,
            repartitions=[
                mutualisation.RepartitionIn(partie="notre_campagne", pourcentage=80),
                mutualisation.RepartitionIn(partie="partie_externe", partie_id=pid, pourcentage=15),
            ],  # Σ = 95
        )
        raised = False
        try:
            mutualisation.create_mutualisee(cid, payload)
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised, "Σ ≠ 100 % aurait dû être rejeté"
    finally:
        teardown(cid)


def test_notre_quote_part_calculee():
    cid = fresh_campaign()
    try:
        pid = mutualisation.create_partie(cid, mutualisation.PartieExterneIn(nom="Amard"))["id"]
        m = mutualisation.create_mutualisee(cid, mutualisation.MutualiseeIn(
            objet="Local Pop'", montant_total_ttc=9800,
            repartitions=[
                mutualisation.RepartitionIn(partie="notre_campagne", pourcentage=93),
                mutualisation.RepartitionIn(partie="partie_externe", partie_id=pid, pourcentage=7),
            ],
        ))
        assert m["notre_quote_part"] == 9114.0          # 93 % de 9800
        montants = {r["pourcentage"]: r["montant"] for r in m["repartitions"]}
        assert montants[93.0] == 9114.0 and montants[7.0] == 686.0
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
