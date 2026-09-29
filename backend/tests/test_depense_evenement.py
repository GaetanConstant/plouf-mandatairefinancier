"""Rattachement d'une dépense à des événements depuis le formulaire de dépense."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import comptes
import evenements
from models import Depense, LiaisonEvenement
from _fixture import fresh_campaign, teardown, run_tests


def _depense(libelle="Bière", montant=120.0, evts=None):
    return Depense(date=date(2026, 2, 10), libelle=libelle, fournisseur="Cave",
                   montant_ttc=montant, tva=0.0, categorie_cnccfp="B1",
                   statut="Payé", evenements=evts)


def _evenement(cid, titre):
    return evenements.create_evenement(cid, evenements.EvenementIn(
        titre=titre, type="reunion_publique", date_debut="2026-02-10"))["id"]


def test_rattache_a_la_creation():
    cid = fresh_campaign()
    try:
        ev = _evenement(cid, "Réunion publique")
        comptes.create_depense(cid, _depense(evts=[LiaisonEvenement(evenement_id=ev)]))
        detail = evenements.detail_evenement(cid, ev)
        assert detail["nb_depenses"] == 1 and detail["cout"] == 120.0, detail
    finally:
        teardown(cid)


def test_rattache_a_la_modification_et_remonte_dans_la_liste():
    cid = fresh_campaign()
    try:
        ev = _evenement(cid, "Meeting")
        comptes.create_depense(cid, _depense())
        d = comptes.list_depenses(cid)[0]
        assert d["evenements"] == [], d["evenements"]

        comptes.update_depense(cid, d["id"], _depense(
            evts=[LiaisonEvenement(evenement_id=ev, quote_part=50)]))

        d = comptes.list_depenses(cid)[0]
        assert d["evenements"] == [
            {"evenement_id": ev, "titre": "Meeting", "quote_part": 50.0}], d["evenements"]
        assert evenements.detail_evenement(cid, ev)["cout"] == 60.0
    finally:
        teardown(cid)


def test_ventilation_sur_deux_evenements():
    cid = fresh_campaign()
    try:
        e1, e2 = _evenement(cid, "E1"), _evenement(cid, "E2")
        comptes.create_depense(cid, _depense(montant=100.0, evts=[
            LiaisonEvenement(evenement_id=e1, quote_part=30),
            LiaisonEvenement(evenement_id=e2, quote_part=70),
        ]))
        assert evenements.detail_evenement(cid, e1)["cout"] == 30.0
        assert evenements.detail_evenement(cid, e2)["cout"] == 70.0
    finally:
        teardown(cid)


def test_somme_superieure_a_100_rejetee():
    cid = fresh_campaign()
    try:
        e1, e2 = _evenement(cid, "E1"), _evenement(cid, "E2")
        raised = False
        try:
            comptes.create_depense(cid, _depense(evts=[
                LiaisonEvenement(evenement_id=e1, quote_part=60),
                LiaisonEvenement(evenement_id=e2, quote_part=60),
            ]))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised, "120 % aurait dû être rejeté"
    finally:
        teardown(cid)


def test_liste_vide_detache():
    cid = fresh_campaign()
    try:
        ev = _evenement(cid, "Meeting")
        comptes.create_depense(cid, _depense(evts=[LiaisonEvenement(evenement_id=ev)]))
        d = comptes.list_depenses(cid)[0]
        comptes.update_depense(cid, d["id"], _depense(evts=[]))
        assert comptes.list_depenses(cid)[0]["evenements"] == []
        assert evenements.detail_evenement(cid, ev)["nb_depenses"] == 0
    finally:
        teardown(cid)


def test_champ_absent_preserve_les_liaisons():
    """Un appelant qui ignore le champ ne doit rien détacher.

    Le rattachement fait depuis la page Événements survivrait mal à une simple
    correction de montant si l'absence du champ valait « détache tout ».
    """
    cid = fresh_campaign()
    try:
        ev = _evenement(cid, "Meeting")
        comptes.create_depense(cid, _depense())
        d = comptes.list_depenses(cid)[0]
        evenements.link_depense(cid, ev, evenements.LiaisonIn(depense_id=d["id"]))

        comptes.update_depense(cid, d["id"], _depense(montant=200.0))  # evenements=None

        assert evenements.detail_evenement(cid, ev)["nb_depenses"] == 1
        assert comptes.list_depenses(cid)[0]["evenements"][0]["evenement_id"] == ev
    finally:
        teardown(cid)


def test_meme_evenement_deux_fois_rejete():
    cid = fresh_campaign()
    try:
        ev = _evenement(cid, "Meeting")
        raised = False
        try:
            comptes.create_depense(cid, _depense(evts=[
                LiaisonEvenement(evenement_id=ev, quote_part=30),
                LiaisonEvenement(evenement_id=ev, quote_part=30),
            ]))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised, "le doublon aurait dû être rejeté"
    finally:
        teardown(cid)


def test_evenement_inexistant_rejete():
    cid = fresh_campaign()
    try:
        raised = False
        try:
            comptes.create_depense(cid, _depense(evts=[LiaisonEvenement(evenement_id=999)]))
        except HTTPException as e:
            raised = True
            assert e.status_code == 404
        assert raised, "un événement inexistant aurait dû donner un 404"
    finally:
        teardown(cid)


def test_depense_non_validee_ne_gonfle_pas_le_cout():
    """Ce que dépose l'équipe attend l'arbitrage, y compris dans le coût d'un événement.

    Rattacher une dépense depuis son formulaire est ouvert à l'équipe, alors que
    la page Événements est réservée au mandataire. Sans ce filtre, un dépôt non
    validé déplacerait immédiatement le coût affiché.
    """
    cid = fresh_campaign()
    try:
        ev = _evenement(cid, "Meeting")
        comptes.create_depense(cid, _depense(montant=500.0,
                                             evts=[LiaisonEvenement(evenement_id=ev)]),
                               auteur="militant", role="equipe")
        detail = evenements.detail_evenement(cid, ev)
        assert detail["cout"] == 0.0, detail["cout"]
        assert detail["nb_depenses"] == 0, detail["nb_depenses"]
        assert detail["depenses"] == [], detail["depenses"]
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
