"""Calendrier de campagne : bornes de l'axe et placement des activités."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import calendrier
import evenements
from db.models import Election
from db.session import campaign_session
from db.helpers import election_id
from db import enums
from _fixture import fresh_campaign, teardown, run_tests


def _datee(cid: str, tour1: str, tour2: str | None = None) -> None:
    with campaign_session(cid) as s:
        e = s.get(Election, election_id(s))
        e.date_tour1 = date.fromisoformat(tour1)
        e.date_tour2 = date.fromisoformat(tour2) if tour2 else None


def test_axe_borne_par_le_scrutin_pas_par_le_depot():
    """Le calendrier couvre la campagne ; le dépôt est trois mois plus tard."""
    cid = fresh_campaign()
    try:
        _datee(cid, "2026-09-27")
        d = calendrier.donnees(cid)
        assert d["fin"] == "2026-09-27"
        assert any(j["libelle"].startswith("Date limite de dépôt") for j in d["jalons_apres"])
    finally:
        teardown(cid)


def test_le_second_tour_prolonge_le_calendrier():
    cid = fresh_campaign()
    try:
        _datee(cid, "2026-03-15", "2026-03-22")
        assert calendrier.donnees(cid)["fin"] == "2026-03-22"
    finally:
        teardown(cid)


def test_un_evenement_couvre_ses_semaines():
    """Un événement de dix jours s'étale sur les colonnes qu'il traverse."""
    cid = fresh_campaign()
    try:
        _datee(cid, "2026-09-27")
        evenements.create_evenement(cid, evenements.EvenementIn(
            titre="Porte à porte Tonkin", type="porte_a_porte",
            date_debut="2026-06-01", date_fin="2026-06-10"))

        groupes = {g["titre"]: g for g in calendrier.donnees(cid)["groupes"]}
        ligne = groupes["Porte à porte"]["lignes"][0]
        assert ligne["largeur"] >= 2, "du 1er au 10 juin, l'activité traverse deux semaines"
    finally:
        teardown(cid)


def test_evenement_hors_periode_ecarte():
    """Un événement postérieur au scrutin ne doit pas étirer l'axe en silence."""
    cid = fresh_campaign()
    try:
        _datee(cid, "2026-09-27")
        evenements.create_evenement(cid, evenements.EvenementIn(
            titre="Pot de clôture", type="reception", date_debut="2026-11-15"))

        d = calendrier.donnees(cid)
        assert d["fin"] == "2026-09-27"
        assert all(g["titre"] != "Réceptions" for g in d["groupes"])
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
