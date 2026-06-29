"""Moteur de calcul des échéances légales d'une campagne (spec §3).

Toutes les dates sont calculées à partir de la date du 1er tour (et, pour
l'ouverture de la période de financement, du mois de l'élection).

⚠️ La date officielle de dépôt publiée par l'administration prime toujours sur
le calcul théorique : prévoir une surcharge manuelle (`Election.date_depot_surcharge`).
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date, timedelta

log = logging.getLogger(__name__)

FRIDAY = 4  # date.weekday() : lundi=0 … vendredi=4 … dimanche=6


def add_months(d: date, months: int) -> date:
    """Ajoute (ou retranche) un nombre de mois en bornant le jour au mois cible."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def friday_before(d: date) -> date:
    """Dernier vendredi strictement antérieur à `d`."""
    offset = (d.weekday() - FRIDAY) % 7
    if offset == 0:  # `d` est un vendredi → le vendredi précédent
        offset = 7
    return d - timedelta(days=offset)


def first_friday_after(d: date) -> date:
    """Premier vendredi strictement postérieur à `d`."""
    offset = (FRIDAY - d.weekday()) % 7
    if offset == 0:  # `d` est un vendredi → le vendredi suivant
        offset = 7
    return d + timedelta(days=offset)


def ouverture_periode_financement(date_election: date) -> date:
    """1er jour du 6e mois précédant le mois de l'élection."""
    return add_months(date(date_election.year, date_election.month, 1), -6)


def fin_engagement_depenses(date_tour1: date) -> date:
    """Vendredi (minuit) précédant le tour de scrutin."""
    return friday_before(date_tour1)


def date_limite_depot(date_tour1: date) -> date:
    """10e vendredi suivant le 1er tour (dépôt à 18h ce jour-là).

    On part du 1er vendredi strictement postérieur au tour, puis +9 semaines.
    """
    return first_friday_after(date_tour1) + timedelta(weeks=9)


def date_cloture_compte(date_limite_depot_: date) -> date:
    """Date limite de dépôt + 6 mois."""
    return add_months(date_limite_depot_, 6)


@dataclass
class JalonsCampagne:
    ouverture_periode_financement: date
    fin_engagement_depenses: date
    date_limite_depot: date
    date_cloture_compte: date
    cessation_fonctions_mandataire: date


def calculer_jalons(date_tour1: date, date_depot_surcharge: date | None = None) -> JalonsCampagne:
    """Calcule tous les jalons. Si une date de dépôt officielle est fournie,
    elle prime et sert de base au calcul de la clôture / cessation.
    """
    depot = date_depot_surcharge or date_limite_depot(date_tour1)
    if date_depot_surcharge:
        log.info("Date de dépôt surchargée (officielle) : %s", date_depot_surcharge)
    cloture = date_cloture_compte(depot)
    return JalonsCampagne(
        ouverture_periode_financement=ouverture_periode_financement(date_tour1),
        fin_engagement_depenses=fin_engagement_depenses(date_tour1),
        date_limite_depot=depot,
        date_cloture_compte=cloture,
        cessation_fonctions_mandataire=cloture,
    )
