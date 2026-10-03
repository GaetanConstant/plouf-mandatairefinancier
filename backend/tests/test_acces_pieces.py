"""Accès aux pièces justificatives : cloisonnement par campagne et chemins.

Les pièces étaient montées en statique, donc lisibles sans session par qui
connaissait l'URL. Ces tests couvrent la logique d'autorisation de la route qui
les remplace ; l'exigence de session elle-même tient aux dépendances déclarées
sur la route, vérifiées structurellement ci-dessous.
"""

import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import comptes
import main
from database import UPLOADS_DIR, get_central_db_connection, init_central_db
from models import Depense
from _fixture import fresh_campaign, teardown, run_tests


# Sur un dépôt fraîchement cloné, la base centrale n'existe pas : ces tests
# écrivent dans `campaigns`, que seule cette initialisation crée. En local la
# table existait déjà, ce qui masquait l'échec jusqu'à l'intégration continue.
init_central_db()


def _fichier(nom: str) -> str:
    (Path(UPLOADS_DIR) / nom).write_bytes(b"%PDF-1.4 piece confidentielle")
    return nom


def _declarer(cid: str):
    """Inscrit la campagne au registre central, que la route interroge."""
    with get_central_db_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO campaigns (id, name, db_path) VALUES (?,?,?)",
                     [cid, cid, f"{cid}.sqlite"])


def _oublier(cid: str):
    with get_central_db_connection() as conn:
        conn.execute("DELETE FROM campaigns WHERE id = ?", [cid])


def _depense_avec_piece(cid, fichier):
    comptes.create_depense(cid, Depense(
        date=date(2026, 9, 1), libelle="Facture", fournisseur="F",
        montant_ttc=100.0, tva=0.0, categorie_cnccfp="A1", statut="Payé",
        justificatif_path=fichier))


def _servir(nom, cid):
    return main.servir_piece(nom, current_user={"username": "x"}, campaign_id=cid, _garde="mandataire")


def test_la_route_exige_une_session_et_une_campagne():
    """Garde structurelle : retirer une dépendance rouvrirait l'accès public."""
    import inspect
    from auth import get_current_user
    from deps import get_campaign_conn
    defauts = [p.default for p in inspect.signature(main.servir_piece).parameters.values()]
    dependances = [d.dependency for d in defauts if hasattr(d, "dependency")]
    assert get_current_user in dependances, "la route ne vérifie plus la session"
    assert get_campaign_conn in dependances, "la route n'est plus cloisonnée par campagne"


def test_le_mandataire_lit_la_piece_de_sa_campagne():
    cid = fresh_campaign()
    nom = _fichier("test_acces_mien.pdf")
    try:
        _declarer(cid)
        _depense_avec_piece(cid, nom)
        reponse = _servir(nom, cid)
        assert Path(reponse.path).name == nom
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        _oublier(cid); teardown(cid)


def test_la_piece_d_une_autre_campagne_est_refusee():
    """`uploads` est commun : un testeur ne doit pas lire le dossier d'un autre."""
    cid_a, cid_b = fresh_campaign(), fresh_campaign()
    nom = _fichier("test_acces_voisin.pdf")
    try:
        _declarer(cid_a); _declarer(cid_b)
        _depense_avec_piece(cid_b, nom)            # la pièce appartient à B
        raised = False
        try:
            _servir(nom, cid_a)
        except HTTPException as e:
            raised = True
            assert e.status_code == 403, e.status_code
        assert raised, "la pièce du voisin aurait dû être refusée"
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        _oublier(cid_a); _oublier(cid_b); teardown(cid_a); teardown(cid_b)


def test_un_orphelin_reste_lisible():
    """Sans ça, impossible de regarder un fichier avant de le supprimer."""
    cid = fresh_campaign()
    nom = _fichier("test_acces_orphelin.pdf")
    try:
        _declarer(cid)
        assert Path(_servir(nom, cid).path).name == nom
    finally:
        (Path(UPLOADS_DIR) / nom).unlink(missing_ok=True)
        _oublier(cid); teardown(cid)


def test_pas_de_remontee_hors_du_dossier():
    """Un nom de fichier n'est pas un chemin."""
    cid = fresh_campaign()
    try:
        _declarer(cid)
        for piege in ["../config.py", "../../etc/passwd", "....//config.py"]:
            raised = False
            try:
                _servir(piege, cid)
            except HTTPException as e:
                raised = True
                assert e.status_code == 404, (piege, e.status_code)
            assert raised, piege
    finally:
        _oublier(cid); teardown(cid)


def test_un_fichier_absent_donne_404():
    cid = fresh_campaign()
    try:
        _declarer(cid)
        raised = False
        try:
            _servir("jamais_depose.pdf", cid)
        except HTTPException as e:
            raised = True
            assert e.status_code == 404
        assert raised
    finally:
        _oublier(cid); teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
