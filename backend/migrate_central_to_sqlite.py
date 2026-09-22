"""Migration ponctuelle du référentiel central DuckDB (`central.db`) vers SQLite.

À jouer une seule fois, avec DuckDB encore installé :

    uv run --with duckdb python migrate_central_to_sqlite.py

Idempotent : recrée `central.sqlite` à partir de `central.db` à chaque passage.
Le fichier DuckDB d'origine n'est pas modifié.
"""

from __future__ import annotations

import logging
import os
import sqlite3

import duckdb

from database import CENTRAL_DB_PATH, DATA_DIR, init_central_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LEGACY_DB_PATH = os.path.join(DATA_DIR, "central.db")
TABLES = {
    "users": ("username", "full_name", "hashed_password", "role"),
    "campaigns": ("id", "name", "db_path"),
    "user_campaigns": ("username", "campaign_id"),
}


def migrate() -> None:
    if not os.path.exists(LEGACY_DB_PATH):
        raise SystemExit(f"Base DuckDB introuvable : {LEGACY_DB_PATH}")

    init_central_db()
    src = duckdb.connect(LEGACY_DB_PATH, read_only=True)
    dst = sqlite3.connect(CENTRAL_DB_PATH, isolation_level=None)
    try:
        for table, columns in TABLES.items():
            rows = src.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
            dst.execute(f"DELETE FROM {table}")
            dst.executemany(
                f"INSERT INTO {table} ({', '.join(columns)}) "
                f"VALUES ({', '.join('?' * len(columns))})",
                rows,
            )
            logger.info("%s : %d lignes migrées", table, len(rows))
    finally:
        src.close()
        dst.close()
    logger.info("Base centrale SQLite écrite : %s", CENTRAL_DB_PATH)


if __name__ == "__main__":
    migrate()
