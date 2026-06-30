"""Helpers de tests : campagne SQLite jetable, isolée et nettoyée.

Chaque test provisionne une base de campagne neuve (create_all, rapide),
seed le minimum, puis la supprime. Pas de dépendance pytest : les fichiers
de test exposent un harnais __main__ comme tests/test_election_dates.py.
"""

from __future__ import annotations

import os
import sys
import uuid

# backend/ sur le sys.path quand on lance `uv run python tests/test_x.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import (  # noqa: E402
    init_campaign_schema,
    campaign_db_path,
    campaign_session,
    _ENGINES,
    _SESSION_FACTORIES,
)
from db.models import Election  # noqa: E402
from db import enums  # noqa: E402


def fresh_campaign(plafond: float = 154781.0, with_election: bool = True) -> str:
    """Crée une base de campagne neuve et retourne son campaign_id."""
    cid = "pytest_" + uuid.uuid4().hex[:8]
    init_campaign_schema(cid)
    if with_election:
        with campaign_session(cid) as s:
            s.add(Election(type=enums.TypeElection.municipale, libelle="Test",
                           plafond_depenses=plafond))
    return cid


def teardown(cid: str) -> None:
    """Ferme l'engine caché et supprime le fichier SQLite de test."""
    eng = _ENGINES.pop(cid, None)
    _SESSION_FACTORIES.pop(cid, None)
    if eng is not None:
        eng.dispose()
    path = campaign_db_path(cid)
    if os.path.exists(path):
        os.remove(path)


def run_tests(globals_dict: dict) -> int:
    """Harnais sans pytest : exécute toutes les fonctions test_* du module."""
    tests = [v for k, v in sorted(globals_dict.items())
             if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"  ❌ {t.__name__} : {e!r}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"  💥 {t.__name__} : {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests OK")
    return 1 if failures else 0
