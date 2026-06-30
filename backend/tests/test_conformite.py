"""Tests du moteur de conformité : chaque cause de rejet (bloquant) + prêt à déposer."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import conformite
from db.session import campaign_session
from db.models import Donateur, Recette, Mandataire
from db import enums
from _fixture import fresh_campaign, teardown, run_tests


def _codes(cid, niveau=None):
    res = conformite.run_checks(cid)
    return {a["code"] for a in res["alertes"] if niveau is None or a["niveau"] == niveau}, res


def _add_don(cid, montant=100.0, mode=enums.ModePaiement.cheque, **donateur_kw):
    donateur_kw.setdefault("est_personne_physique", True)
    with campaign_session(cid) as s:
        d = Donateur(nom="X", **donateur_kw)
        s.add(d)
        s.flush()
        s.add(Recette(donateur_id=d.id, categorie=enums.CategorieRecette.don,
                      montant=montant, date_versement=date(2026, 1, 10),
                      mode=mode, rubrique_imputation="7010"))


def test_don_personne_morale_bloquant():
    cid = fresh_campaign()
    try:
        _add_don(cid, est_personne_physique=False)
        codes, res = _codes(cid, "bloquant")
        assert "don_personne_morale" in codes
        assert res["pret_a_deposer"] is False
    finally:
        teardown(cid)


def test_don_etranger_bloquant():
    cid = fresh_campaign()
    try:
        _add_don(cid, nationalite="Belge", pays_residence="Belgique")
        codes, _ = _codes(cid, "bloquant")
        assert "don_etranger" in codes
    finally:
        teardown(cid)


def test_don_francais_ou_resident_ok():
    cid = fresh_campaign()
    try:
        _add_don(cid, nationalite="Belge", pays_residence="France")  # résident FR
        codes, _ = _codes(cid, "bloquant")
        assert "don_etranger" not in codes
    finally:
        teardown(cid)


def test_don_especes_sup_150_bloquant():
    cid = fresh_campaign()
    try:
        _add_don(cid, montant=200, mode=enums.ModePaiement.especes)
        codes, _ = _codes(cid, "bloquant")
        assert "don_especes_sup_150" in codes
    finally:
        teardown(cid)


def test_plafond_donateur_bloquant():
    cid = fresh_campaign()
    try:
        with campaign_session(cid) as s:
            d = Donateur(nom="Riche", est_personne_physique=True, nationalite="Française")
            s.add(d); s.flush()
            for _ in range(2):
                s.add(Recette(donateur_id=d.id, categorie=enums.CategorieRecette.don,
                              montant=3000, date_versement=date(2026, 1, 10),
                              mode=enums.ModePaiement.cheque, rubrique_imputation="7010"))
        codes, _ = _codes(cid, "bloquant")
        assert "plafond_donateur" in codes  # 6000 > 4600
    finally:
        teardown(cid)


def test_especes_globales_bloquant():
    cid = fresh_campaign(plafond=20000.0)  # ≥ 15000 → plafond espèces actif
    try:
        # 20% de 20000 = 4000 ; on met 5000 en espèces (par dons ≤150 pour éviter l'autre bloquant)
        with campaign_session(cid) as s:
            for i in range(50):
                d = Donateur(nom=f"D{i}", est_personne_physique=True, nationalite="Française")
                s.add(d); s.flush()
                s.add(Recette(donateur_id=d.id, categorie=enums.CategorieRecette.don,
                              montant=100, date_versement=date(2026, 1, 10),
                              mode=enums.ModePaiement.especes, rubrique_imputation="7010"))
        codes, _ = _codes(cid, "bloquant")
        assert "especes_globales" in codes  # 5000 > 4000
    finally:
        teardown(cid)


def test_plafond_depasse_bloquant():
    cid = fresh_campaign(plafond=1000.0)
    try:
        from db.models import Depense
        with campaign_session(cid) as s:
            s.add(Depense(montant_ttc=1500, rubrique_imputation="A1",
                          statut=enums.StatutDepense.paye, reglee=True))
        codes, _ = _codes(cid, "bloquant")
        assert "plafond_depasse" in codes  # 1500 > 1000
    finally:
        teardown(cid)


def test_mandataire_interdiction_bancaire_bloquant():
    cid = fresh_campaign()
    try:
        with campaign_session(cid) as s:
            from db.models import Election
            from sqlalchemy import select
            eid = s.scalars(select(Election)).first().id
            s.add(Mandataire(election_id=eid, type=enums.TypeMandataire.physique,
                             interdiction_bancaire=True, incompatibilites_verifiees=True))
        codes, _ = _codes(cid, "bloquant")
        assert "mandataire_interdiction_bancaire" in codes
    finally:
        teardown(cid)


def test_pret_a_deposer_sans_bloquant():
    cid = fresh_campaign()
    try:
        _add_don(cid, montant=100, mode=enums.ModePaiement.cheque,
                 nationalite="Française")
        res = conformite.run_checks(cid)
        assert res["compteurs"]["bloquant"] == 0
        assert res["pret_a_deposer"] is True
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
