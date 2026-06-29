"""Factory d'engine / session SQLAlchemy : un fichier SQLite par campagne.

Pendant la transition, les nouvelles bases ORM utilisent l'extension `.sqlite`
pour ne pas écraser les anciens fichiers DuckDB `<id>.db`. Le script de
migration lit l'ancien `.db` (DuckDB) et écrit le nouveau `.sqlite` (SQLAlchemy).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from database import CAMPAIGNS_DIR
from db.base import Base
# Import des modèles pour que Base.metadata soit peuplée (effet de bord requis).
import db.models  # noqa: F401

_ENGINES: dict[str, Engine] = {}
_SESSION_FACTORIES: dict[str, sessionmaker] = {}


def campaign_db_path(campaign_id: str) -> str:
    """Chemin du fichier SQLite ORM d'une campagne."""
    return os.path.join(CAMPAIGNS_DIR, f"{campaign_id}.sqlite")


def get_engine(campaign_id: str) -> Engine:
    """Retourne (en le créant/cachant) l'engine SQLite d'une campagne."""
    if campaign_id not in _ENGINES:
        path = campaign_db_path(campaign_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        engine = create_engine(
            f"sqlite:///{path}",
            future=True,
            connect_args={"check_same_thread": False},
        )
        _ENGINES[campaign_id] = engine
        _SESSION_FACTORIES[campaign_id] = sessionmaker(bind=engine, expire_on_commit=False)
    return _ENGINES[campaign_id]


def init_campaign_schema(campaign_id: str) -> None:
    """Crée les tables manquantes pour une campagne (dev / bootstrap).

    En production, les migrations sont gérées par Alembic ; cette fonction reste
    utile pour initialiser rapidement une base de campagne neuve.
    """
    engine = get_engine(campaign_id)
    Base.metadata.create_all(engine)


def provision_campaign_db(campaign_id: str) -> None:
    """Crée la base SQLite d'une campagne et l'amène à head via Alembic.

    Idempotent. Config sans fichier .ini pour ne pas perturber le logging.
    """
    from alembic import command
    from alembic.config import Config

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = campaign_db_path(campaign_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(cfg, "head")


def ensure_campaign_db(campaign_id: str) -> None:
    """Provisionne la base de campagne si son fichier SQLite n'existe pas encore."""
    if not os.path.exists(campaign_db_path(campaign_id)):
        provision_campaign_db(campaign_id)


def get_session(campaign_id: str) -> Session:
    """Ouvre une nouvelle session (à fermer par l'appelant)."""
    get_engine(campaign_id)
    return _SESSION_FACTORIES[campaign_id]()


@contextmanager
def campaign_session(campaign_id: str) -> Iterator[Session]:
    """Session transactionnelle : commit si succès, rollback sinon, fermeture systématique."""
    session = get_session(campaign_id)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
