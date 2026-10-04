"""Suppression d'une campagne : qui en a le droit.

Un bêta-testeur ne pouvait pas supprimer sa propre campagne d'essai : la route
exigeait le rôle d'administrateur du compte.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import main
from database import (ROLE_MANDATAIRE, ROLE_EQUIPE, get_central_db_connection,
                      init_central_db)
from _fixture import fresh_campaign, teardown, run_tests

init_central_db()


def _rattacher(cid, user, role):
    with get_central_db_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO campaigns (id, name, db_path) VALUES (?,?,?)",
                     [cid, cid, f"{cid}.sqlite"])
        conn.execute("INSERT OR REPLACE INTO user_campaigns (username, campaign_id, role) "
                     "VALUES (?,?,?)", [user, cid, role])


def _oublier(cid):
    with get_central_db_connection() as conn:
        conn.execute("DELETE FROM user_campaigns WHERE campaign_id = ?", [cid])
        conn.execute("DELETE FROM campaigns WHERE id = ?", [cid])


def test_le_mandataire_supprime_sa_campagne():
    cid = fresh_campaign()
    try:
        _rattacher(cid, "u_sup1", ROLE_MANDATAIRE)
        res = main.delete_campaign(cid, {"username": "u_sup1", "role": "user"})
        assert "supprimée" in res["message"], res
    finally:
        _oublier(cid); teardown(cid)


def test_l_equipe_ne_supprime_pas():
    """Déposer une pièce ne donne pas le droit d'effacer le dossier."""
    cid = fresh_campaign()
    try:
        _rattacher(cid, "u_sup2", ROLE_EQUIPE)
        raised = False
        try:
            main.delete_campaign(cid, {"username": "u_sup2", "role": "user"})
        except HTTPException as e:
            raised = True
            assert e.status_code == 403, e.status_code
        assert raised
    finally:
        _oublier(cid); teardown(cid)


def test_un_etranger_ne_supprime_pas():
    cid = fresh_campaign()
    try:
        _rattacher(cid, "u_sup3", ROLE_MANDATAIRE)
        raised = False
        try:
            main.delete_campaign(cid, {"username": "u_inconnu", "role": "user"})
        except HTTPException as e:
            raised = True
            assert e.status_code == 403
        assert raised
    finally:
        _oublier(cid); teardown(cid)


def test_l_administrateur_supprime_toujours():
    cid = fresh_campaign()
    try:
        _rattacher(cid, "u_sup4", ROLE_MANDATAIRE)
        res = main.delete_campaign(cid, {"username": "autre", "role": "admin"})
        assert "supprimée" in res["message"], res
    finally:
        _oublier(cid); teardown(cid)


def test_la_liste_indique_mon_role():
    """L'écran doit savoir s'il peut proposer la suppression."""
    cid = fresh_campaign()
    try:
        _rattacher(cid, "u_sup5", ROLE_MANDATAIRE)
        lignes = main.list_my_campaigns({"username": "u_sup5", "role": "user"})
        mienne = [c for c in lignes if c["id"] == cid]
        assert mienne and mienne[0]["mon_role"] == ROLE_MANDATAIRE, lignes
    finally:
        _oublier(cid); teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
