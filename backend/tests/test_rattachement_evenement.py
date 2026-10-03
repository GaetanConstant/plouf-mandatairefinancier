"""Rattachement des dépenses aux événements, et son décompte dans le reste à faire."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import completude
import comptes
import evenements
from models import Depense, LiaisonEvenement
from _fixture import fresh_campaign, teardown, run_tests


def _depense(cid, libelle="Colle", evts=None, hors=None):
    comptes.create_depense(cid, Depense(
        date=date(2026, 2, 10), libelle=libelle, fournisseur="Papeterie",
        montant_ttc=42.0, tva=0.0, categorie_cnccfp="B2", statut="Payé",
        evenements=evts, hors_evenement=hors))
    return comptes.list_depenses(cid)[0]["id"]


def _evenement(cid, titre="Collage"):
    return evenements.create_evenement(cid, evenements.EvenementIn(
        titre=titre, type="tractage", date_debut="2026-02-10"))["id"]


def _section(cid):
    return {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["evenements"]


def test_depense_sans_evenement_compte_dans_le_restant():
    cid = fresh_campaign()
    try:
        _depense(cid)
        sec = _section(cid)
        assert sec["requis"] == 1 and sec["remplis"] == 0, sec
        assert sec["actions"][0]["type"] == "evenement", sec["actions"]
    finally:
        teardown(cid)


def test_depense_rattachee_sort_du_restant():
    cid = fresh_campaign()
    try:
        ev = _evenement(cid)
        _depense(cid, evts=[LiaisonEvenement(evenement_id=ev)])
        assert _section(cid)["complet"]
    finally:
        teardown(cid)


def test_hors_evenement_est_un_arbitrage_qui_compte_comme_fait():
    """« Rien à rattacher » doit se distinguer de « pas encore rattaché »."""
    cid = fresh_campaign()
    try:
        did = _depense(cid)
        assert not _section(cid)["complet"]
        comptes.rattacher_evenement(cid, did, comptes.RattachementIn(evenement_id=None))
        assert _section(cid)["complet"]
    finally:
        teardown(cid)


def test_rattachement_depuis_le_reste_a_faire():
    cid = fresh_campaign()
    try:
        ev = _evenement(cid, "Collage du 10")
        did = _depense(cid)
        comptes.rattacher_evenement(cid, did, comptes.RattachementIn(evenement_id=ev))
        assert _section(cid)["complet"]
        assert evenements.detail_evenement(cid, ev)["nb_depenses"] == 1
    finally:
        teardown(cid)


def test_rattacher_leve_le_hors_evenement():
    """Les deux ne peuvent pas être vrais : une dépense située n'est pas hors événement."""
    cid = fresh_campaign()
    try:
        ev = _evenement(cid)
        did = _depense(cid, hors=True)
        comptes.rattacher_evenement(cid, did, comptes.RattachementIn(evenement_id=ev))
        assert comptes.list_depenses(cid)[0]["hors_evenement"] is False
    finally:
        teardown(cid)


def test_depense_inexistante_rejetee():
    cid = fresh_campaign()
    try:
        raised = False
        try:
            comptes.rattacher_evenement(cid, 999, comptes.RattachementIn(evenement_id=None))
        except HTTPException as e:
            raised = True
            assert e.status_code == 404
        assert raised
    finally:
        teardown(cid)


def test_chaque_manque_porte_de_quoi_le_traiter():
    cid = fresh_campaign()
    try:
        _depense(cid)
        sans_action = [s["titre"] for s in completude.evaluer(cid)["sections"]
                       if not s["complet"] and not s["actions"]]
        assert not sans_action, sans_action
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
