"""Une campagne sans élection enregistrée doit rester utilisable.

Deux bêta-testeurs ont buté dessus : enregistrer un emprunt ou déposer un
récépissé échouait sur une contrainte d'intégrité tant que l'écran Identité
n'avait jamais été enregistré — et l'écran n'affichait rien.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

import annexes
import identite
from database import UPLOADS_DIR
from db.helpers import election_id
from db.models import Election
from db.session import campaign_session
from _fixture import fresh_campaign, teardown, run_tests


def _neuve():
    """Une campagne telle qu'un testeur vient de la créer : rien de saisi."""
    return fresh_campaign(with_election=False)


def test_un_emprunt_s_enregistre_sans_identite_saisie():
    cid = _neuve()
    try:
        annexes.create_emprunt(cid, annexes.EmpruntIn(
            type="parti", preteur_nom="FRANCE INSOUMISE", montant=2000.0))
        assert len(annexes.list_emprunts(cid)) == 1
    finally:
        teardown(cid)


def test_un_recepisse_se_depose_sans_identite_saisie():
    cid = _neuve()
    nom = "test_recepisse_implicite.pdf"
    (Path(UPLOADS_DIR) / nom).write_bytes(b"%PDF-1.4 recepisse")
    try:
        for cle in ("recepisse-candidature", "recepisse-mandataire"):
            identite.save_piece_declarative(
                cid, cle, identite.PieceDeclarativeIn(fichier=nom), "gaetan")
        fournies = [p["cle"] for p in identite.list_pieces_declaratives(cid) if p["fournie"]]
        assert set(fournies) == {"recepisse-candidature", "recepisse-mandataire"}, fournies
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid)


def test_l_election_n_est_creee_qu_une_fois():
    """Plusieurs appels ne doivent pas multiplier les élections."""
    cid = _neuve()
    try:
        annexes.create_emprunt(cid, annexes.EmpruntIn(type="banque", montant=100.0))
        annexes.create_emprunt(cid, annexes.EmpruntIn(type="banque", montant=200.0))
        with campaign_session(cid) as s:
            assert len(list(s.scalars(select(Election)).all())) == 1
    finally:
        teardown(cid)


def test_une_election_existante_n_est_pas_remplacee():
    cid = fresh_campaign()  # avec élection « Test »
    try:
        with campaign_session(cid) as s:
            avant = election_id(s)
            assert election_id(s) == avant
            assert s.scalars(select(Election)).first().libelle == "Test"
    finally:
        teardown(cid)


def test_on_peut_demander_sans_creer():
    """Les lectures ne doivent pas fabriquer d'élection au passage."""
    cid = _neuve()
    try:
        with campaign_session(cid) as s:
            assert election_id(s, creer=False) is None
            assert list(s.scalars(select(Election)).all()) == []
    finally:
        teardown(cid)


def test_la_completude_reclame_toujours_le_nom():
    """La ligne créée à vide ne doit pas faire croire le candidat renseigné.

    Un texte factice — « À renseigner » — aurait compté comme rempli et masqué
    un vrai manque au dépôt.
    """
    import completude
    cid = _neuve()
    nom = "test_recepisse_vide.pdf"
    (Path(UPLOADS_DIR) / nom).write_bytes(b"%PDF-1.4 recepisse")
    try:
        identite.save_piece_declarative(
            cid, "recepisse-candidature", identite.PieceDeclarativeIn(fichier=nom), "gaetan")
        sec = {s["cle"]: s for s in completude.evaluer(cid)["sections"]}["candidat"]
        assert "Nom" in sec["manquants"] and "Prénom" in sec["manquants"], sec["manquants"]
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
