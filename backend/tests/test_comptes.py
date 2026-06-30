"""Tests des invariants comptes : plafond 4 600 €/donateur + statistiques."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import comptes
from models import Recette, Depense
from _fixture import fresh_campaign, teardown, run_tests


def _recette(type_="Don", montant=100.0, nom="DUPONT Jean", d="2026-01-10"):
    return Recette(date=date.fromisoformat(d), nom_donateur=nom, adresse="1 rue X",
                   montant=montant, type=type_)


def _depense(montant=100.0, statut="Payé", cat="A1", is_nature=False, d="2026-01-10"):
    return Depense(date=date.fromisoformat(d), libelle="Test", fournisseur="Four",
                   montant_ttc=montant, tva=0.0, categorie_cnccfp=cat, statut=statut,
                   is_nature=is_nature)


def test_plafond_donateur_sous_seuil_ok():
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, _recette(montant=4000))
        comptes.create_recette(cid, _recette(montant=500))  # total 4500 ≤ 4600
        assert sum(r["montant"] for r in comptes.list_recettes(cid)) == 4500
    finally:
        teardown(cid)


def test_plafond_donateur_depasse_rejete():
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, _recette(montant=4000))
        raised = False
        try:
            comptes.create_recette(cid, _recette(montant=700))  # 4700 > 4600
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised, "le 2e don aurait dû être rejeté (>4600€)"
    finally:
        teardown(cid)


def test_plafond_ne_concerne_que_les_dons():
    cid = fresh_campaign()
    try:
        # Un apport de 10000 ne doit PAS déclencher le plafond donateur.
        comptes.create_recette(cid, _recette(type_="Apport", montant=10000, nom="Le Candidat"))
        assert sum(r["montant"] for r in comptes.list_recettes(cid)) == 10000
    finally:
        teardown(cid)


def test_plafond_par_donateur_independant():
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, _recette(montant=4600, nom="A A"))
        comptes.create_recette(cid, _recette(montant=4600, nom="B B"))  # autre donateur
        assert len(comptes.list_recettes(cid)) == 2
    finally:
        teardown(cid)


def test_stats_plafond_et_nature():
    cid = fresh_campaign(plafond=154781.0)
    try:
        comptes.create_depense(cid, _depense(montant=1000, statut="Payé"))
        comptes.create_depense(cid, _depense(montant=300, is_nature=True))  # nature
        comptes.create_recette(cid, _recette(montant=2000))
        s = comptes.compute_stats(cid)
        assert s["plafond"] == 154781.0
        assert s["total_depenses"] == 1300.0           # tout, nature comprise
        assert s["total_nature_hors_tresorerie"] == 300.0
        assert s["total_depenses_payees"] == 1000.0     # nature exclue de la trésorerie
        assert s["total_recettes"] == 2000.0
        assert abs(s["consommation_plafond"] - (1300 / 154781 * 100)) < 1e-6
        assert s["solde_tresorerie"] == 1000.0          # 2000 - 1000 payé
    finally:
        teardown(cid)


def test_stats_nombre_donateurs_dons_seulement():
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, _recette(type_="Don", nom="A A", montant=50))
        comptes.create_recette(cid, _recette(type_="Don", nom="B B", montant=50))
        comptes.create_recette(cid, _recette(type_="Apport", nom="Candidat", montant=50))
        assert comptes.compute_stats(cid)["nombre_donateurs"] == 2  # apport non compté
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
