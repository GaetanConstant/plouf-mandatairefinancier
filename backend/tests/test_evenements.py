"""Tests événements : coût par quote-part + garde Σ quote-parts d'une dépense ≤ 100 %."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import comptes
import evenements
from models import Depense
from db.session import campaign_session
from db.models import Depense as ORMDepense
from sqlalchemy import select
from _fixture import fresh_campaign, teardown, run_tests


def _add_depense(cid, montant):
    comptes.create_depense(cid, Depense(date=date(2026, 1, 10), libelle="Salle",
                                        fournisseur="F", montant_ttc=montant, tva=0.0,
                                        categorie_cnccfp="B1", statut="Payé"))
    with campaign_session(cid) as s:
        return s.scalars(select(ORMDepense).order_by(ORMDepense.id.desc())).first().id


def test_cout_par_quote_part():
    cid = fresh_campaign()
    try:
        ev = evenements.create_evenement(cid, evenements.EvenementIn(
            titre="Meeting", type="meeting", date_debut="2026-02-10"))["id"]
        d1 = _add_depense(cid, 2000)
        d2 = _add_depense(cid, 500)
        evenements.link_depense(cid, ev, evenements.LiaisonIn(depense_id=d1, quote_part=50))
        evenements.link_depense(cid, ev, evenements.LiaisonIn(depense_id=d2))  # None → 100%
        detail = evenements.detail_evenement(cid, ev)
        assert detail["cout"] == 1500.0   # 2000*0.5 + 500*1.0
        assert detail["nb_depenses"] == 2
    finally:
        teardown(cid)


def test_garde_quote_part_superieure_100():
    cid = fresh_campaign()
    try:
        ev1 = evenements.create_evenement(cid, evenements.EvenementIn(
            titre="E1", type="autre", date_debut="2026-02-10"))["id"]
        ev2 = evenements.create_evenement(cid, evenements.EvenementIn(
            titre="E2", type="autre", date_debut="2026-02-11"))["id"]
        d = _add_depense(cid, 1000)
        evenements.link_depense(cid, ev1, evenements.LiaisonIn(depense_id=d, quote_part=50))
        raised = False
        try:
            # 50 (ev1) + 60 (ev2) = 110 % > 100 %
            evenements.link_depense(cid, ev2, evenements.LiaisonIn(depense_id=d, quote_part=60))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised, "Σ quote-parts > 100 % aurait dû être rejeté"
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
