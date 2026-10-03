"""Requalification d'une recette : changer un don en prêt, et ce que ça protège."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import comptes
import maincourante
from db.models import CarnetRecus, RecuDon
from db.session import campaign_session
from db.helpers import election_id
from db import enums
from models import Recette
from _fixture import fresh_campaign, teardown, run_tests


def _recette(cid, type_="Don", montant=2000.0, nom="Union de la gauche"):
    comptes.create_recette(cid, Recette(
        date=date(2026, 9, 8), nom_donateur=nom, adresse="1 rue X",
        montant=montant, type=type_))
    return comptes.list_recettes(cid)[0]["id"]


def _dto(type_="Pret", montant=2000.0, nom="Union de la gauche"):
    return Recette(date=date(2026, 9, 8), nom_donateur=nom, adresse="1 rue X",
                   montant=montant, type=type_)


def test_un_don_devient_un_pret():
    cid = fresh_campaign()
    try:
        rid = _recette(cid, "Don")
        comptes.update_recette(cid, rid, _dto("Pret"))
        assert comptes.list_recettes(cid)[0]["type"] == "Pret"
    finally:
        teardown(cid)


def test_la_rubrique_comptable_suit_le_type():
    """Requalifier sans changer la rubrique laisserait un prêt imputé en 7010."""
    cid = fresh_campaign()
    try:
        rid = _recette(cid, "Don")
        avant = {l["sens"]: l["rubrique"] for l in maincourante.journal(cid)}["recette"]
        comptes.update_recette(cid, rid, _dto("Pret"))
        apres = {l["sens"]: l["rubrique"] for l in maincourante.journal(cid)}["recette"]
        assert avant != apres, (avant, apres)
    finally:
        teardown(cid)


def test_le_suivi_d_attestation_tombe_hors_don():
    """« Reçu envoyé » n'a plus de sens sur un prêt."""
    cid = fresh_campaign()
    try:
        rid = _recette(cid, "Don")
        comptes.toggle_recette_sent(cid, rid)
        assert comptes.list_recettes(cid)[0]["recu_genere"] is True
        comptes.update_recette(cid, rid, _dto("Pret"))
        assert comptes.list_recettes(cid)[0]["recu_genere"] is False
    finally:
        teardown(cid)


def test_un_recu_du_carnet_bloque_la_requalification():
    """Un reçu détaché porte un numéro remis au donateur : on l'annule d'abord."""
    cid = fresh_campaign()
    try:
        rid = _recette(cid, "Don", montant=500.0, nom="MOREAU Sylvie")
        with campaign_session(cid) as s:
            carnet = CarnetRecus(election_id=election_id(s), numero_carnet="C1",
                                 numero_formule_debut=1, numero_formule_fin=50)
            s.add(carnet)
            s.flush()
            s.add(RecuDon(numero_formule=1, carnet_id=carnet.id, recette_id=rid,
                          montant=500.0, statut=enums.StatutRecuDon.delivre))
        raised = False
        try:
            comptes.update_recette(cid, rid, _dto("Pret", montant=500.0, nom="MOREAU Sylvie"))
        except HTTPException as e:
            raised = True
            assert e.status_code == 409 and "carnet" in e.detail
        assert raised, "la requalification aurait dû être refusée"
        assert comptes.list_recettes(cid)[0]["type"] == "Don"
    finally:
        teardown(cid)


def test_un_recu_annule_ne_bloque_plus():
    """Annuler le reçu dans le carnet est précisément ce qui débloque."""
    cid = fresh_campaign()
    try:
        rid = _recette(cid, "Don", montant=500.0, nom="MOREAU Sylvie")
        with campaign_session(cid) as s:
            carnet = CarnetRecus(election_id=election_id(s), numero_carnet="C1",
                                 numero_formule_debut=1, numero_formule_fin=50)
            s.add(carnet)
            s.flush()
            s.add(RecuDon(numero_formule=1, carnet_id=carnet.id, recette_id=rid,
                          montant=500.0, statut=enums.StatutRecuDon.annule))
        comptes.update_recette(cid, rid, _dto("Pret", montant=500.0, nom="MOREAU Sylvie"))
        assert comptes.list_recettes(cid)[0]["type"] == "Pret"
    finally:
        teardown(cid)


def test_un_don_reste_modifiable_en_don():
    """Le garde-fou ne doit pas empêcher de corriger un montant ou une adresse."""
    cid = fresh_campaign()
    try:
        rid = _recette(cid, "Don", montant=500.0, nom="MOREAU Sylvie")
        with campaign_session(cid) as s:
            carnet = CarnetRecus(election_id=election_id(s), numero_carnet="C1",
                                 numero_formule_debut=1, numero_formule_fin=50)
            s.add(carnet)
            s.flush()
            s.add(RecuDon(numero_formule=1, carnet_id=carnet.id, recette_id=rid,
                          montant=500.0, statut=enums.StatutRecuDon.delivre))
        comptes.update_recette(cid, rid, Recette(
            date=date(2026, 9, 9), nom_donateur="MOREAU Sylvie",
            adresse="2 rue Y", montant=600.0, type="Don"))
        r = comptes.list_recettes(cid)[0]
        assert r["montant"] == 600.0 and r["adresse"] == "2 rue Y", r
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
