"""Relevés PDF mensuels : la pièce de l'enveloppe B, à part des imports."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import completude
import depot
import identite
import releves
import releves_mensuels
from releves_mensuels import mois_attendus
from _fixture import fresh_campaign, teardown, run_tests


def _mois_precedent(jour: date, n: int = 1) -> date:
    annee, mois = jour.year, jour.month - n
    while mois < 1:
        annee, mois = annee - 1, mois + 12
    return date(annee, mois, 1)


def _section(cid):
    return {s["cle"]: s for s in completude.evaluer(cid)["sections"]}.get("releves_pdf")


def _ouvrir(cid, ouverture, cloture=None):
    identite.save_mandataire(cid, identite.MandataireIn(type="physique", nom="Test"))
    releves_mensuels.enregistrer_periode_compte(cid, releves_mensuels.PeriodeCompteIn(
        date_ouverture=ouverture.isoformat(),
        date_cloture=cloture.isoformat() if cloture else None))


def test_un_compte_ouvert_n_exige_pas_le_mois_en_cours():
    assert mois_attendus(date(2026, 9, 11), None, date(2026, 10, 19)) == ["2026-09"]
    assert mois_attendus(date(2026, 10, 2), None, date(2026, 10, 19)) == []
    assert mois_attendus(date(2025, 11, 5), None, date(2026, 1, 3)) == ["2025-11", "2025-12"]


def test_un_compte_clos_exige_son_mois_de_cloture():
    assert mois_attendus(date(2026, 9, 11), date(2026, 11, 3), date(2027, 2, 1)) == \
        ["2026-09", "2026-10", "2026-11"]


def test_chaque_mois_du_compte_attend_son_pdf():
    cid = fresh_campaign()
    try:
        ouverture = _mois_precedent(date.today(), 2)
        _ouvrir(cid, ouverture)
        sec = _section(cid)
        assert sec["requis"] == 2 and sec["remplis"] == 0, sec
        assert sec["actions"][0]["type"] == "releve_mensuel"

        premier = f"{ouverture.year:04d}-{ouverture.month:02d}"
        releves_mensuels.deposer(cid, releves_mensuels.ReleveMensuelIn(
            fichier="releve_sept.pdf", periode=premier), "gaetan")
        sec = _section(cid)
        assert sec["remplis"] == 1 and premier not in " ".join(sec["manquants"])
        assert any(p["fichier"] == "releve_sept.pdf" for p in depot.get_depot(cid)["pieces_B"]), \
            "le PDF entre au dossier, en enveloppe B"
    finally:
        teardown(cid)


def test_le_csv_importe_n_est_plus_une_piece_du_dossier():
    cid = fresh_campaign()
    try:
        releves.create_releve(cid, releves.ReleveIn(
            libelle="Jour", source="csv", fichier="export_du_jour.csv",
            transactions=[releves.TransactionIn(
                date_operation="2026-09-12", libelle="VIR", montant=10.0)]), "gaetan")
        assert not any(p["fichier"] == "export_du_jour.csv"
                       for p in depot.get_depot(cid)["pieces_B"])
        assert releves.list_releves(cid)[0]["fichier"] == "export_du_jour.csv", \
            "le fichier reste attaché à son import"
    finally:
        teardown(cid)


def test_sans_date_d_ouverture_la_premiere_ligne_sert_de_depart():
    cid = fresh_campaign()
    try:
        debut = _mois_precedent(date.today(), 1)
        releves.create_releve(cid, releves.ReleveIn(
            libelle="Import", source="csv",
            transactions=[releves.TransactionIn(
                date_operation=debut.isoformat(), libelle="VIR", montant=10.0)]), "gaetan")
        etat = releves_mensuels.etat(cid)
        assert etat["ouverture_deduite"]
        assert etat["manquants"] == [f"{debut.year:04d}-{debut.month:02d}"]
    finally:
        teardown(cid)


def test_un_pdf_sans_mois_se_date_apres_coup():
    cid = fresh_campaign()
    try:
        _ouvrir(cid, date(2026, 9, 11), date(2026, 9, 30))
        releves_mensuels.deposer(cid, releves_mensuels.ReleveMensuelIn(
            fichier="ancien.pdf", periode="2026-09"), "gaetan")
        doc_id = releves_mensuels.etat(cid)["mois"][0]["documents"][0]["id"]
        # Simule un PDF versé avant cette version : sans mois.
        from db.session import campaign_session
        from db.models import Document
        with campaign_session(cid) as s:
            s.get(Document, doc_id).periode = None
        etat = releves_mensuels.etat(cid)
        assert etat["manquants"] == ["2026-09"] and len(etat["a_dater"]) == 1

        etat = releves_mensuels.dater(cid, doc_id, releves_mensuels.DaterIn(periode="2026-09"))
        assert etat["manquants"] == [] and etat["a_dater"] == []
    finally:
        teardown(cid)


def test_une_cloture_avant_l_ouverture_est_refusee():
    cid = fresh_campaign()
    try:
        try:
            _ouvrir(cid, date(2026, 9, 11), date(2026, 8, 1))
            raise AssertionError("aurait dû être refusé")
        except HTTPException as e:
            assert e.status_code == 400
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
