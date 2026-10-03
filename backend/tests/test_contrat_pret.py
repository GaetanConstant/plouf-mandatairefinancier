"""Contrat de prêt : exigé au dépôt, et créateur de l'emprunt."""

import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import annexes
import completude
import comptes
from database import UPLOADS_DIR
from models import Recette
from _fixture import fresh_campaign, teardown, run_tests


def _recette(cid, type_="Pret", montant=2000.0, nom="FRANCE INSOUMISE"):
    comptes.create_recette(cid, Recette(
        date=date(2026, 9, 22), nom_donateur=nom, adresse="1 rue X",
        montant=montant, type=type_))
    return comptes.list_recettes(cid)[0]["id"]


def _section(cid):
    return {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["contrats_pret"]


def _fichier(nom):
    (Path(UPLOADS_DIR) / nom).write_bytes(b"%PDF-1.4 contrat")
    return nom


def test_un_pret_sans_contrat_est_signale():
    cid = fresh_campaign()
    try:
        _recette(cid)
        sec = _section(cid)
        assert sec["requis"] == 1 and sec["remplis"] == 0, sec
        assert sec["actions"][0]["type"] == "contrat_pret", sec["actions"]
    finally:
        teardown(cid)


def test_un_pret_sans_contrat_bloque_le_depot():
    cid = fresh_campaign()
    try:
        _recette(cid)
        etat = completude.evaluer(cid)
        assert any("Contrats de prêt" in m for m in etat["manquants"]), etat["manquants"]
        assert not etat["complet"]
    finally:
        teardown(cid)


def test_deposer_le_contrat_cree_l_emprunt():
    """L'emprunt n'existait pas : c'est le contrat qui le fait naître."""
    cid = fresh_campaign()
    nom = _fichier("test_contrat_pret.pdf")
    try:
        rid = _recette(cid, montant=2000.0, nom="FRANCE INSOUMISE")
        assert annexes.list_emprunts(cid) == []

        annexes.emprunt_de_recette(cid, rid, nom, auteur="gaetan", role="mandataire")

        emprunts = annexes.list_emprunts(cid)
        assert len(emprunts) == 1, emprunts
        e = emprunts[0]
        # Le prêteur, le montant et la date viennent de la recette.
        assert e["preteur_nom"] == "FRANCE INSOUMISE", e
        assert e["montant"] == 2000.0 and e["date_contrat"] == "2026-09-22", e
        assert e["contrat_fichier"] == nom, e
        assert _section(cid)["complet"]
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid)


def test_ni_taux_ni_duree_ne_sont_exiges():
    """Seul le contrat est demandé ; le reste se complète dans l'onglet Emprunts."""
    cid = fresh_campaign()
    nom = _fichier("test_contrat_minimal.pdf")
    try:
        rid = _recette(cid)
        annexes.emprunt_de_recette(cid, rid, nom, auteur="g", role="mandataire")
        e = annexes.list_emprunts(cid)[0]
        assert e["taux"] is None and e["duree_mois"] is None, e
        assert _section(cid)["complet"]
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid)


def test_un_second_depot_remplace_le_contrat():
    cid = fresh_campaign()
    a, b = _fichier("test_contrat_a.pdf"), _fichier("test_contrat_b.pdf")
    try:
        rid = _recette(cid)
        annexes.emprunt_de_recette(cid, rid, a, auteur="g", role="mandataire")
        annexes.emprunt_de_recette(cid, rid, b, auteur="g", role="mandataire")
        emprunts = annexes.list_emprunts(cid)
        # Un seul emprunt, pas un par dépôt.
        assert len(emprunts) == 1 and emprunts[0]["contrat_fichier"] == b, emprunts
    finally:
        for f in (a, b):
            (Path(UPLOADS_DIR) / f).unlink(missing_ok=True)
        teardown(cid)


def test_un_don_n_appelle_pas_de_contrat():
    cid = fresh_campaign()
    nom = _fichier("test_contrat_don.pdf")
    try:
        rid = _recette(cid, type_="Don", montant=300.0, nom="MOREAU Sylvie")
        assert _section(cid)["requis"] == 0
        raised = False
        try:
            annexes.emprunt_de_recette(cid, rid, nom, auteur="g", role="mandataire")
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid)


def test_chaque_manque_porte_de_quoi_le_traiter():
    cid = fresh_campaign()
    try:
        _recette(cid)
        sans_action = [s["titre"] for s in completude.evaluer(cid)["sections"]
                       if not s["complet"] and not s["actions"]]
        assert not sans_action, sans_action
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
