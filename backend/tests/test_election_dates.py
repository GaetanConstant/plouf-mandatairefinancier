"""Tests du moteur de dates (spec §3).

Compatibles pytest. Exécutables aussi sans pytest via le harnais en fin de fichier.
"""

from datetime import date

import election_dates as ed


# ── helpers ────────────────────────────────────────────────────────────────

def _count_fridays(after: date, through: date) -> int:
    """Nombre de vendredis dans l'intervalle ]after, through]."""
    n = 0
    d = ed.first_friday_after(after)
    while d <= through:
        n += 1
        d += __import__("datetime").timedelta(weeks=1)
    return n


# ── add_months ──────────────────────────────────────────────────────────────

def test_add_months_recule_de_six():
    assert ed.add_months(date(2026, 3, 1), -6) == date(2025, 9, 1)


def test_add_months_borne_le_jour():
    # 31 janvier + 1 mois → 28 février (pas de 31 février)
    assert ed.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_add_months_passe_annee():
    assert ed.add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)


# ── vendredis ────────────────────────────────────────────────────────────────

def test_friday_before_dimanche():
    # 2026-03-15 est un dimanche
    assert date(2026, 3, 15).weekday() == 6
    assert ed.friday_before(date(2026, 3, 15)) == date(2026, 3, 13)


def test_friday_before_strict_si_vendredi():
    vendredi = date(2026, 3, 13)
    assert vendredi.weekday() == 4
    assert ed.friday_before(vendredi) == date(2026, 3, 6)


def test_first_friday_after_dimanche():
    assert ed.first_friday_after(date(2026, 3, 15)) == date(2026, 3, 20)


def test_first_friday_after_strict_si_vendredi():
    assert ed.first_friday_after(date(2026, 3, 13)) == date(2026, 3, 20)


# ── jalons légaux ────────────────────────────────────────────────────────────

def test_ouverture_periode_financement():
    # Élection en mars 2026 → ouverture 1er septembre 2025
    assert ed.ouverture_periode_financement(date(2026, 3, 15)) == date(2025, 9, 1)


def test_date_limite_depot_est_le_10e_vendredi():
    tour1 = date(2026, 3, 15)  # dimanche
    limite = ed.date_limite_depot(tour1)
    assert limite.weekday() == 4  # un vendredi
    assert _count_fridays(tour1, limite) == 10  # le 10e après le tour
    assert limite == date(2026, 5, 22)


def test_date_cloture_compte():
    assert ed.date_cloture_compte(date(2026, 5, 22)) == date(2026, 11, 22)


def test_calculer_jalons_complet():
    j = ed.calculer_jalons(date(2026, 3, 15))
    assert j.ouverture_periode_financement == date(2025, 9, 1)
    assert j.fin_engagement_depenses == date(2026, 3, 13)
    assert j.date_limite_depot == date(2026, 5, 22)
    assert j.date_cloture_compte == date(2026, 11, 22)
    assert j.cessation_fonctions_mandataire == date(2026, 11, 22)


def test_surcharge_date_officielle_prime():
    officielle = date(2026, 5, 29)  # ex. date publiée par la préfecture
    j = ed.calculer_jalons(date(2026, 3, 15), date_depot_surcharge=officielle)
    assert j.date_limite_depot == officielle
    assert j.date_cloture_compte == date(2026, 11, 29)  # +6 mois sur l'officielle


# ── harnais sans pytest ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"  ❌ {t.__name__} : {e!r}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests OK")
    sys.exit(1 if failures else 0)
