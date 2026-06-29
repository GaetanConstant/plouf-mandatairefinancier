"""Échéancier : calcul dynamique des échéances légales d'une campagne (spec §3).

S'appuie sur le moteur de dates (election_dates) et l'entité Election. Chaque
jalon est daté et qualifié (passé / aujourd'hui / à venir) par rapport à la date
du jour.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select

import election_dates
from db.models import Election
from db.session import campaign_session, ensure_campaign_db


def _statut(d: date | None, today: date) -> str:
    if d is None:
        return "indetermine"
    if d < today:
        return "passe"
    if d == today:
        return "aujourdhui"
    return "a_venir"


def echeances(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    today = datetime.now().date()
    with campaign_session(campaign_id) as s:
        e = s.scalars(select(Election)).first()
        if not e or not e.date_tour1:
            return []
        j = election_dates.calculer_jalons(e.date_tour1, e.date_depot_surcharge)

    jalons = [
        ("Ouverture de la période de financement", j.ouverture_periode_financement,
         "1er jour du 6e mois précédant le mois de l'élection"),
        ("Fin d'engagement des dépenses", j.fin_engagement_depenses,
         "Vendredi minuit précédant le 1er tour"),
        ("Date limite de dépôt du compte", j.date_limite_depot,
         "10e vendredi suivant le 1er tour, 18h"),
        ("Clôture du compte bancaire", j.date_cloture_compte,
         "Date limite de dépôt + 6 mois"),
        ("Cessation des fonctions du mandataire", j.cessation_fonctions_mandataire,
         "6 mois après le dépôt"),
    ]
    return [
        {"libelle": libelle, "date": d.isoformat(), "statut": _statut(d, today), "regle": regle}
        for libelle, d, regle in jalons
    ]
