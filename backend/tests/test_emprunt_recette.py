"""Un emprunt saisi doit entrer dans la comptabilité.

Un bêta-testeur voulait « voir s'il s'inscrit après sur la main courante et
sur les recettes ». Il ne s'inscrivait pas : l'onglet Emprunts vivait à côté.
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import annexes
import comptes
import maincourante
from db.session import campaign_session
from db.models import Donateur
from sqlalchemy import select
from _fixture import fresh_campaign, teardown, run_tests


def _emprunt(cid, type_="parti", nom="FRANCE INSOUMISE", montant=2000.0,
             date_contrat="2026-09-22"):
    return annexes.create_emprunt(cid, annexes.EmpruntIn(
        type=type_, preteur_nom=nom, montant=montant, date_contrat=date_contrat))


def test_un_emprunt_cree_sa_recette():
    cid = fresh_campaign()
    try:
        _emprunt(cid)
        recettes = comptes.list_recettes(cid)
        assert len(recettes) == 1, recettes
        r = recettes[0]
        assert r["type"] == "Pret" and r["montant"] == 2000.0, r
        assert r["nom_donateur"] == "FRANCE INSOUMISE", r
        assert r["date"] == "2026-09-22", r
    finally:
        teardown(cid)


def test_la_recette_apparait_en_main_courante_en_7030():
    cid = fresh_campaign()
    try:
        _emprunt(cid)
        lignes = [l for l in maincourante.journal(cid) if l["sens"] == "recette"]
        assert len(lignes) == 1 and lignes[0]["rubrique"] == "7030", lignes
        assert lignes[0]["num_piece"] == "R001", lignes
    finally:
        teardown(cid)


def test_un_preteur_moral_n_est_pas_une_personne_physique():
    """Le distinguer importe pour les contrôles de dons."""
    cid = fresh_campaign()
    try:
        _emprunt(cid, type_="parti", nom="FRANCE INSOUMISE")
        with campaign_session(cid) as s:
            d = s.scalars(select(Donateur)).first()
            assert d.est_personne_physique is False, d.nom
    finally:
        teardown(cid)


def test_un_preteur_physique_reste_une_personne_physique():
    cid = fresh_campaign()
    try:
        _emprunt(cid, type_="personne_physique", nom="DUPONT")
        with campaign_session(cid) as s:
            assert s.scalars(select(Donateur)).first().est_personne_physique is True
    finally:
        teardown(cid)


def test_supprimer_l_emprunt_conserve_la_recette():
    """L'argent est entré sur le compte : l'effacer fausserait les totaux."""
    cid = fresh_campaign()
    try:
        eid = _emprunt(cid)["id"]
        annexes.delete_emprunt(cid, eid)
        assert annexes.list_emprunts(cid) == []
        recettes = comptes.list_recettes(cid)
        assert len(recettes) == 1 and recettes[0]["montant"] == 2000.0, recettes
    finally:
        teardown(cid)


def test_sans_date_de_contrat_la_recette_est_datee_du_jour():
    cid = fresh_campaign()
    try:
        _emprunt(cid, date_contrat=None)
        assert comptes.list_recettes(cid)[0]["date"] == date.today().isoformat()
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
