"""Migration des données campagne : DuckDB (legacy) → SQLite (ORM SQLAlchemy).

- Lit l'ancienne base ``data/campaigns/<id>.db`` (DuckDB) en LECTURE SEULE.
- Écrit une nouvelle base ``data/campaigns/<id>.sqlite`` (schéma Alembic).
- Idempotent : la cible est recréée à neuf (``--force`` pour écraser une cible
  existante). La source DuckDB n'est jamais modifiée.

Chaque hypothèse de mapping (champ inconnu dans le legacy) est journalisée.

Usage :
    uv run python migrate_duckdb_to_sqlite.py                 # toutes les campagnes
    uv run python migrate_duckdb_to_sqlite.py <id> [<id>...]  # ciblées
    uv run python migrate_duckdb_to_sqlite.py --force         # écrase les .sqlite existants
"""

from __future__ import annotations

import argparse
import logging
import os
import unicodedata

import duckdb
from alembic import command
from alembic.config import Config

from database import CAMPAIGNS_DIR, CENTRAL_DB_PATH
from db import enums
from db.models import Depense, Document, Donateur, Election, Recette
from db.session import campaign_db_path, get_session

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("migration")

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

_RUBRIQUE_RECETTE = {
    enums.CategorieRecette.don: "7010",
    enums.CategorieRecette.apport_perso: "7020",
    enums.CategorieRecette.pret: "7030",
    enums.CategorieRecette.contribution_parti: "7040",
}
_RUBRIQUE_RECETTE_DEFAUT = "7050"
_RUBRIQUE_DEPENSE_DEFAUT = "I1"  # legacy = texte libre → à re-catégoriser via l'UI
_EXTENSIONS_FICHIER = (".pdf", ".png", ".jpg", ".jpeg", ".heic", ".webp", ".docx", ".xlsx")


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _norm(s: str | None) -> str:
    return _strip_accents((s or "").strip().lower())


def _map_categorie_recette(legacy_type: str | None) -> enums.CategorieRecette:
    t = _norm(legacy_type)
    if t.startswith("don"):
        return enums.CategorieRecette.don
    if t.startswith("pret"):
        return enums.CategorieRecette.pret
    if t.startswith("apport"):
        return enums.CategorieRecette.apport_perso
    if "parti" in t or t == "fi":
        return enums.CategorieRecette.contribution_parti
    log.warning("  type de recette inconnu '%s' → 'don' par défaut", legacy_type)
    return enums.CategorieRecette.don


def _clean_donor_name(raw: str | None) -> str:
    """Retire le préfixe « Don / Dons / Prêt / Apport » du nom de donateur."""
    name = (raw or "").strip()
    low = _norm(name)
    for prefix in ("dons ", "don ", "prets ", "pret ", "apport "):
        if low.startswith(prefix):
            return name[len(prefix):].strip()
    return name


def _map_statut_depense(legacy_statut: str | None) -> tuple[enums.StatutDepense, bool]:
    s = _norm(legacy_statut)
    if s == "paye":
        return enums.StatutDepense.paye, True
    if s == "facture":
        return enums.StatutDepense.facture, False
    return enums.StatutDepense.engage, False


def _guess_type_election(name: str) -> enums.TypeElection:
    n = _norm(name)
    if "metropol" in n:
        return enums.TypeElection.metropole
    if "municipal" in n:
        return enums.TypeElection.municipale
    if "secteur" in n:
        return enums.TypeElection.secteur
    return enums.TypeElection.autre


def _looks_like_file(libelle: str | None) -> bool:
    return bool(libelle) and libelle.strip().lower().endswith(_EXTENSIONS_FICHIER)


def _create_target_schema(campaign_id: str, force: bool) -> bool:
    """Crée le fichier SQLite cible et applique les migrations Alembic.

    Retourne False si la cible existe déjà et que --force n'est pas demandé.
    """
    new_path = campaign_db_path(campaign_id)
    if os.path.exists(new_path):
        if not force:
            log.warning("Cible déjà présente, ignorée (utiliser --force) : %s", new_path)
            return False
        os.remove(new_path)
        log.info("Cible existante supprimée (--force) : %s", new_path)

    # Config sans fichier .ini : évite fileConfig() qui désactiverait nos loggers
    # et remettrait le niveau racine à WARN. On fournit juste l'essentiel.
    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{new_path}")
    command.upgrade(cfg, "head")
    return True


def _campaign_name(campaign_id: str) -> str:
    conn = duckdb.connect(CENTRAL_DB_PATH, read_only=True)
    try:
        row = conn.execute("SELECT name FROM campaigns WHERE id = ?", [campaign_id]).fetchone()
        return row[0] if row else campaign_id
    finally:
        conn.close()


def migrate_campaign(campaign_id: str, force: bool = False) -> None:
    old_path = os.path.join(CAMPAIGNS_DIR, f"{campaign_id}.db")
    if not os.path.exists(old_path):
        log.error("Base DuckDB introuvable pour %s : %s", campaign_id, old_path)
        return

    log.info("=== Campagne %s ===", campaign_id)
    if not _create_target_schema(campaign_id, force):
        return

    name = _campaign_name(campaign_id)
    src = duckdb.connect(old_path, read_only=True)
    session = get_session(campaign_id)

    stats = {"recettes": 0, "depenses": 0, "donateurs": 0, "documents": 0,
             "mode_inconnu": 0, "rubrique_defaut": 0, "recu_genere_ignore": 0}
    donateurs: dict[str, Donateur] = {}

    try:
        # Election stub (racine de campagne ; dates à compléter via module Identité).
        election = Election(
            type=_guess_type_election(name),
            libelle=name,
            plafond_depenses=154781.0,  # valeur historiquement codée en dur (à confirmer)
        )
        session.add(election)
        log.info("Election stub créée : %s (type=%s, plafond=154781 à confirmer, dates à compléter)",
                 name, election.type.value)

        # Recettes
        rows = src.execute(
            "SELECT date, nom_donateur, montant, type, recu_genere FROM recettes"
        ).fetchall()
        for d, nom_donateur, montant, type_, recu_genere in rows:
            categorie = _map_categorie_recette(type_)
            nom = _clean_donor_name(nom_donateur) or "Inconnu"
            don = donateurs.get(nom)
            if don is None:
                don = Donateur(nom=nom, est_personne_physique=True)
                session.add(don)
                donateurs[nom] = don
                stats["donateurs"] += 1
            session.add(Recette(
                donateur=don,
                categorie=categorie,
                montant=float(montant or 0),
                date_versement=d,
                mode=None,  # inconnu dans le legacy
                rubrique_imputation=_RUBRIQUE_RECETTE.get(categorie, _RUBRIQUE_RECETTE_DEFAUT),
            ))
            stats["recettes"] += 1
            stats["mode_inconnu"] += 1
            if recu_genere:
                stats["recu_genere_ignore"] += 1

        # Depenses
        rows = src.execute(
            "SELECT date, libelle, fournisseur, montant_ttc, tva, categorie_cnccfp, "
            "statut, justificatif_path FROM depenses"
        ).fetchall()
        for d, libelle, fournisseur, montant_ttc, tva, categorie, statut, justif in rows:
            statut_enum, reglee = _map_statut_depense(statut)
            facture_doc_id = None
            fichier = justif or (libelle if _looks_like_file(libelle) else None)
            if fichier:
                doc = Document(
                    type=enums.TypeDocument.facture,
                    fichier=fichier,
                    enveloppe=enums.Enveloppe.A,
                )
                session.add(doc)
                session.flush()  # pour obtenir doc.id
                facture_doc_id = doc.id
                stats["documents"] += 1
            session.add(Depense(
                fournisseur=fournisseur,
                nature=categorie or libelle,  # libellé humain = ancienne catégorie
                montant_ttc=float(montant_ttc or 0),
                tva=float(tva) if tva is not None else None,
                date_reglement=d,
                mode=None,  # inconnu dans le legacy
                rubrique_imputation=_RUBRIQUE_DEPENSE_DEFAUT,  # à re-catégoriser
                statut=statut_enum,
                reglee=reglee,
                facture_doc_id=facture_doc_id,
            ))
            stats["depenses"] += 1
            stats["rubrique_defaut"] += 1

        session.flush()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        src.close()

    log.info("  ✅ %s recettes, %s dépenses, %s donateurs, %s documents",
             stats["recettes"], stats["depenses"], stats["donateurs"], stats["documents"])
    log.info("  ⚠️ hypothèses : mode de versement NULL sur %s recettes ; "
             "rubrique dépense = '%s' (à re-catégoriser) sur %s dépenses ; "
             "%s reçus 'générés' anciens non repris (pas de carnet).",
             stats["mode_inconnu"], _RUBRIQUE_DEPENSE_DEFAUT, stats["rubrique_defaut"],
             stats["recu_genere_ignore"])


def _all_campaign_ids() -> list[str]:
    conn = duckdb.connect(CENTRAL_DB_PATH, read_only=True)
    try:
        return [r[0] for r in conn.execute("SELECT id FROM campaigns").fetchall()]
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migration DuckDB → SQLite (par campagne).")
    parser.add_argument("campaigns", nargs="*", help="ids de campagne (défaut : toutes)")
    parser.add_argument("--force", action="store_true", help="écrase les .sqlite existants")
    args = parser.parse_args()

    ids = args.campaigns or _all_campaign_ids()
    if not ids:
        log.warning("Aucune campagne à migrer.")
        return
    for cid in ids:
        migrate_campaign(cid, force=args.force)


if __name__ == "__main__":
    main()
