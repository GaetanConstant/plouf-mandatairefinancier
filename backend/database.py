"""Base centrale de l'application : utilisateurs, campagnes et droits d'accès.

Stockage SQLite (`data/central.sqlite`). Les données métier de chaque campagne
vivent dans leur propre fichier `data/campaigns/<id>.sqlite`, géré par
SQLAlchemy + Alembic (voir `db/session.py`).
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CAMPAIGNS_DIR = os.path.join(DATA_DIR, "campaigns")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
CENTRAL_DB_PATH = os.path.join(DATA_DIR, "central.sqlite")

os.makedirs(CAMPAIGNS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Mot de passe initial des comptes semés au premier démarrage. Doit être changé
# à la première connexion (écran « Mon compte »).
_SEED_PASSWORD_HASH = "$2b$12$8kzD/lZzrzY5N1SbcHyQC.xW9a1.9aLeazpcR7N5RV/YxbyGJ48tO"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    full_name TEXT,
    hashed_password TEXT,
    role TEXT DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    name TEXT,
    db_path TEXT
);

CREATE TABLE IF NOT EXISTS user_campaigns (
    username TEXT,
    campaign_id TEXT,
    PRIMARY KEY (username, campaign_id)
);
"""


def _connect() -> sqlite3.Connection:
    """Connexion SQLite en autocommit, avec contraintes de clés actives."""
    conn = sqlite3.connect(CENTRAL_DB_PATH, isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_central_db() -> None:
    """Crée le schéma central et sème les comptes initiaux si la base est vide."""
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        already_seeded = conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        if not already_seeded:
            conn.executemany(
                "INSERT INTO users (username, full_name, hashed_password, role) VALUES (?, ?, ?, ?)",
                [
                    ("gconstant", "Gaëtan CONSTANT MAGNARD", _SEED_PASSWORD_HASH, "admin"),
                    ("mgarabedian", "Mathieu Garabedian", _SEED_PASSWORD_HASH, "user"),
                ],
            )
    finally:
        conn.close()


@contextmanager
def get_central_db_connection() -> Iterator[sqlite3.Connection]:
    """Connexion à la base centrale, fermée systématiquement."""
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()
