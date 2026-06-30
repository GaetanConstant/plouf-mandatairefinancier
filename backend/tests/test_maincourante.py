"""Tests main courante : solde bancaire courant (cumul recettes − dépenses)."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import comptes
import maincourante
from models import Recette, Depense
from _fixture import fresh_campaign, teardown, run_tests


def test_solde_courant_cumule():
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, Recette(date=date(2026, 1, 1), nom_donateur="A A",
                                            adresse="", montant=1000, type="Don"))
        comptes.create_depense(cid, Depense(date=date(2026, 1, 5), libelle="X", fournisseur="F",
                                            montant_ttc=300, tva=0.0, categorie_cnccfp="A1",
                                            statut="Payé"))
        comptes.create_recette(cid, Recette(date=date(2026, 1, 10), nom_donateur="B B",
                                            adresse="", montant=200, type="Don"))
        j = maincourante.journal(cid)
        # tri chronologique : +1000 → 1000 ; -300 → 700 ; +200 → 900
        soldes = [ligne["solde"] for ligne in j]
        assert soldes == [1000.0, 700.0, 900.0]
        assert j[-1]["solde"] == 900.0
    finally:
        teardown(cid)


def test_journal_contient_les_deux_sens():
    cid = fresh_campaign()
    try:
        comptes.create_recette(cid, Recette(date=date(2026, 1, 1), nom_donateur="A A",
                                            adresse="", montant=100, type="Don"))
        comptes.create_depense(cid, Depense(date=date(2026, 1, 2), libelle="X", fournisseur="F",
                                            montant_ttc=50, tva=0.0, categorie_cnccfp="A1",
                                            statut="Engagé"))
        sens = sorted(ligne["sens"] for ligne in maincourante.journal(cid))
        assert sens == ["depense", "recette"]
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
