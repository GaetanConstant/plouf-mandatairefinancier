"""Événements récurrents : génération des dates et création des occurrences."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import comptes
import evenements
from models import Depense, LiaisonEvenement
from _fixture import fresh_campaign, teardown, run_tests

SAMEDI = 5


def test_samedis_entre_deux_bornes():
    d = evenements.dates_hebdomadaires(date(2026, 9, 1), date(2026, 9, 30), SAMEDI)
    assert [x.isoformat() for x in d] == [
        "2026-09-05", "2026-09-12", "2026-09-19", "2026-09-26"], d


def test_bornes_incluses():
    """Un samedi qui tombe pile sur une borne compte."""
    assert evenements.dates_hebdomadaires(date(2026, 9, 5), date(2026, 9, 5), SAMEDI) \
        == [date(2026, 9, 5)]


def test_plage_sans_le_jour_demande():
    assert evenements.dates_hebdomadaires(date(2026, 9, 6), date(2026, 9, 11), SAMEDI) == []


def test_fin_avant_debut_rejetee():
    raised = False
    try:
        evenements.dates_hebdomadaires(date(2026, 9, 30), date(2026, 9, 1), SAMEDI)
    except ValueError:
        raised = True
    assert raised


def test_serie_cree_une_occurrence_par_date():
    cid = fresh_campaign()
    try:
        res = evenements.create_serie(cid, evenements.SerieIn(
            titre="Tractage marché Saint-Jean", type="tractage", lieu="Place du marché",
            dates=["2026-09-05", "2026-09-12", "2026-09-19"]))
        assert res["nb"] == 3, res
        evts = evenements.list_evenements(cid)
        assert len(evts) == 3
        assert {e["date_debut"] for e in evts} == {"2026-09-05", "2026-09-12", "2026-09-19"}
        # Une seule série pour toutes les occurrences.
        assert len({e["serie_id"] for e in evts}) == 1
        assert all(e["titre"] == "Tractage marché Saint-Jean" for e in evts)
    finally:
        teardown(cid)


def test_dates_dedupliquees_et_triees():
    """Le générateur et un ajout manuel peuvent proposer deux fois la même date."""
    cid = fresh_campaign()
    try:
        res = evenements.create_serie(cid, evenements.SerieIn(
            titre="Collage", dates=["2026-09-12", "2026-09-05", "2026-09-12"]))
        assert res["nb"] == 2, res
    finally:
        teardown(cid)


def test_serie_sans_date_rejetee():
    cid = fresh_campaign()
    try:
        raised = False
        try:
            evenements.create_serie(cid, evenements.SerieIn(titre="Vide", dates=[]))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised
    finally:
        teardown(cid)


def test_garde_contre_une_serie_demesuree():
    """Une plage mal saisie ne doit pas créer des milliers d'occurrences."""
    cid = fresh_campaign()
    try:
        trop = [date(2026, 1, 1).replace(day=1).isoformat()] * 0 + [
            (date(2026, 1, 1).toordinal() + n) for n in range(200)]
        dates = [date.fromordinal(o).isoformat() for o in trop]
        raised = False
        try:
            evenements.create_serie(cid, evenements.SerieIn(titre="Trop", dates=dates))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400 and "maximum" in e.detail
        assert raised
    finally:
        teardown(cid)


def test_une_occurrence_porte_ses_propres_depenses():
    """Chaque date est un événement autonome : la dépense se rattache à la bonne."""
    cid = fresh_campaign()
    try:
        evenements.create_serie(cid, evenements.SerieIn(
            titre="Tractage", type="tractage", dates=["2026-09-05", "2026-09-12"]))
        premier, second = sorted(evenements.list_evenements(cid),
                                 key=lambda e: e["date_debut"])
        comptes.create_depense(cid, Depense(
            date=date(2026, 9, 5), libelle="Tracts", fournisseur="Imprimeur",
            montant_ttc=300.0, tva=0.0, categorie_cnccfp="A1", statut="Payé",
            evenements=[LiaisonEvenement(evenement_id=premier["id"])]))
        assert evenements.detail_evenement(cid, premier["id"])["cout"] == 300.0
        assert evenements.detail_evenement(cid, second["id"])["cout"] == 0.0
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
