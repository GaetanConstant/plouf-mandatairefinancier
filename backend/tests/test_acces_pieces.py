"""Accès aux pièces justificatives : session exigée et cloisonnement par campagne.

Les pièces étaient montées en statique, donc lisibles sans session par qui
connaissait l'URL. Ces tests passent par de vraies requêtes HTTP : c'est le
seul moyen de prouver que la session est bien exigée, une vérification du code
ne disant rien du comportement réel de la route.
"""

import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import comptes
import main
from auth import get_password_hash
from database import (UPLOADS_DIR, ROLE_MANDATAIRE, get_central_db_connection,
                      init_central_db)
from models import Depense
from _fixture import fresh_campaign, teardown, run_tests

# Sur un dépôt fraîchement cloné, la base centrale n'existe pas : ces tests
# écrivent dans `campaigns`, que seule cette initialisation crée.
init_central_db()

MOT_DE_PASSE = "motdepasse-de-test"


def _fichier(nom: str) -> str:
    (Path(UPLOADS_DIR) / nom).write_bytes(b"%PDF-1.4 piece confidentielle")
    return nom


def _compte(user: str, cid: str):
    with get_central_db_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO users (username, full_name, hashed_password, role) "
                     "VALUES (?,?,?,?)", [user, user, get_password_hash(MOT_DE_PASSE), "user"])
        conn.execute("INSERT OR REPLACE INTO campaigns (id, name, db_path) VALUES (?,?,?)",
                     [cid, cid, f"{cid}.sqlite"])
        conn.execute("INSERT OR REPLACE INTO user_campaigns (username, campaign_id, role) "
                     "VALUES (?,?,?)", [user, cid, ROLE_MANDATAIRE])


def _oublier(user: str, cid: str):
    with get_central_db_connection() as conn:
        conn.execute("DELETE FROM user_campaigns WHERE campaign_id = ?", [cid])
        conn.execute("DELETE FROM campaigns WHERE id = ?", [cid])
        conn.execute("DELETE FROM users WHERE username = ?", [user])


def _connecte(user: str, cid: str) -> TestClient:
    client = TestClient(main.app)
    r = client.post("/login", json={"username": user, "password": MOT_DE_PASSE})
    assert r.status_code == 200, r.text
    r = client.post(f"/select-campaign/{cid}")
    assert r.status_code == 200, r.text
    return client


def _depense_avec_piece(cid, fichier):
    comptes.create_depense(cid, Depense(
        date=date(2026, 9, 1), libelle="Facture", fournisseur="F",
        montant_ttc=100.0, tva=0.0, categorie_cnccfp="A1", statut="Payé",
        justificatif_path=fichier))


def test_une_piece_n_est_pas_publique():
    """Le défaut corrigé : le dossier était monté en statique, sans session."""
    cid = fresh_campaign()
    nom = _fichier("test_acces_public.pdf")
    try:
        _compte("u_acces1", cid)
        _depense_avec_piece(cid, nom)
        r = TestClient(main.app).get(f"/docs/{nom}")
        assert r.status_code == 401, (r.status_code, r.text)
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        _oublier("u_acces1", cid); teardown(cid)


def test_le_mandataire_lit_la_piece_de_sa_campagne():
    cid = fresh_campaign()
    nom = _fichier("test_acces_mien.pdf")
    try:
        _compte("u_acces2", cid)
        _depense_avec_piece(cid, nom)
        r = _connecte("u_acces2", cid).get(f"/docs/{nom}")
        assert r.status_code == 200 and b"confidentielle" in r.content, r.status_code
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        _oublier("u_acces2", cid); teardown(cid)


def test_la_piece_d_une_autre_campagne_est_refusee():
    """`uploads` est commun : un testeur ne doit pas lire le dossier d'un autre."""
    cid_a, cid_b = fresh_campaign(), fresh_campaign()
    nom = _fichier("test_acces_voisin.pdf")
    try:
        _compte("u_acces3", cid_a); _compte("u_acces4", cid_b)
        _depense_avec_piece(cid_b, nom)            # la pièce appartient à B
        r = _connecte("u_acces3", cid_a).get(f"/docs/{nom}")
        assert r.status_code == 403, (r.status_code, r.text)
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        _oublier("u_acces3", cid_a); _oublier("u_acces4", cid_b)
        teardown(cid_a); teardown(cid_b)


def test_un_orphelin_reste_lisible():
    """Sans ça, impossible de regarder un fichier avant de le supprimer."""
    cid = fresh_campaign()
    nom = _fichier("test_acces_orphelin.pdf")
    try:
        _compte("u_acces5", cid)
        r = _connecte("u_acces5", cid).get(f"/docs/{nom}")
        assert r.status_code == 200, r.status_code
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        _oublier("u_acces5", cid); teardown(cid)


def test_pas_de_remontee_hors_du_dossier():
    """Un nom de fichier n'est pas un chemin."""
    cid = fresh_campaign()
    secret = _fichier("test_acces_secret.pdf")
    try:
        _compte("u_acces6", cid)
        client = _connecte("u_acces6", cid)
        for piege in ["..%2F..%2Fconfig.py", "....//config.py",
                      f"..%2Fuploads%2F{secret}"]:
            r = client.get(f"/docs/{piege}")
            assert r.status_code in (404, 200) and b"SECRET_KEY" not in r.content, piege
            if r.status_code == 200:
                # Seul un nom réduit à son basename peut passer, jamais un chemin.
                assert b"confidentielle" in r.content, piege
    finally:
        (Path(UPLOADS_DIR) / secret).unlink(missing_ok=True)
        _oublier("u_acces6", cid); teardown(cid)


def test_un_fichier_absent_donne_404():
    cid = fresh_campaign()
    try:
        _compte("u_acces7", cid)
        r = _connecte("u_acces7", cid).get("/docs/jamais_depose.pdf")
        assert r.status_code == 404, r.status_code
    finally:
        _oublier("u_acces7", cid); teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
