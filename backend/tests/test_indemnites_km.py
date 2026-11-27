"""Indemnités kilométriques : calcul au barème et justificatif généré."""

import io
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException
from pypdf import PdfReader

import comptes
import indemnites_km as ik
from database import UPLOADS_DIR
from db.models import Depense, Document
from db.session import campaign_session
from _fixture import fresh_campaign, teardown, run_tests


def _trajet(**surcharges) -> ik.IndemniteKmIn:
    valeurs = dict(
        beneficiaire="Gabriel AMARD", qualite="Candidat", vehicule="Fiat 500",
        immatriculation="AA-123-BB", puissance_cv=4, date=date(2026, 9, 23),
        depart="Villeurbanne", arrivee="Mairie de Saint-Martin-en-Haut",
        km_aller=43.5, objet="Réunion publique",
    )
    valeurs.update(surcharges)
    return ik.IndemniteKmIn(**valeurs)


def test_le_montant_suit_le_bareme_fiscal():
    # Les deux IK réelles des sénatoriales du Rhône (D021, D022).
    assert ik.calculer(_trajet())["montant"] == ik.Decimal("52.72")
    assert ik.calculer(_trajet(km_aller=35.4))["montant"] == ik.Decimal("42.90")


def test_aller_simple_et_majoration_electrique():
    assert ik.calculer(_trajet(aller_retour=False))["km_total"] == ik.Decimal("43.5")
    # 87 km × 0,606 × 1,20 = 63,2664 → 63,27
    assert ik.calculer(_trajet(electrique=True))["montant"] == ik.Decimal("63.27")
    # Au-delà de 7 CV, le taux reste celui de « 7 CV et plus ».
    assert ik.taux_km(11) == ik.BAREME_KM[7]


def test_objet_obligatoire():
    cid = fresh_campaign()
    try:
        try:
            ik.creer(cid, _trajet(objet="  "), "gaetan")
            assert False, "un trajet sans objet électoral doit être refusé"
        except HTTPException as e:
            assert e.status_code == 400
    finally:
        teardown(cid)


def test_le_trajet_devient_une_avance_d1_justifiee():
    cid = fresh_campaign()
    carte = Path(UPLOADS_DIR) / "pytest-carte-grise.png"
    # PNG 1×1 valide : suffit pour vérifier que l'annexe est ajoutée.
    carte.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"))
    fichier = None
    try:
        r = ik.creer(cid, _trajet(carte_grise_path=carte.name), "gaetan")
        fichier = Path(UPLOADS_DIR) / r["fichier"]
        assert r["montant"] == 52.72

        with campaign_session(cid) as s:
            d = s.get(Depense, r["id"])
            assert d.rubrique_imputation == "D1" and d.avance_par == "Gabriel AMARD"
            assert "Villeurbanne ↔ Mairie de Saint-Martin-en-Haut" in d.nature
            doc = s.get(Document, d.facture_doc_id)
            assert doc.fichier == r["fichier"] and doc.media_type == "pdf"

        pages = PdfReader(io.BytesIO(fichier.read_bytes())).pages
        assert len(pages) == 2, "justificatif + carte grise en annexe"
        assert "52,72" in pages[0].extract_text()

        # À rembourser à la personne, comme toute avance.
        avances = comptes.avances_a_rembourser(cid)
        assert any(a["personne"] == "Gabriel AMARD" and a["total"] == 52.72 for a in avances), avances
    finally:
        carte.unlink(missing_ok=True)
        if fichier:
            fichier.unlink(missing_ok=True)
        teardown(cid)


if __name__ == "__main__":
    run_tests(globals())
