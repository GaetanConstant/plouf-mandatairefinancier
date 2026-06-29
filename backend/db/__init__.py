"""Couche d'accès aux données (SQLAlchemy ORM) pour la base d'une campagne.

La base `central.db` (utilisateurs / campagnes) reste gérée séparément en SQL
brut dans `database.py`. Ce package gère uniquement le modèle métier d'une
campagne, stocké dans `data/campaigns/<id>.db` (un fichier SQLite par campagne).
"""

from db.base import Base
from db.session import get_engine, get_session, campaign_session, init_campaign_schema

__all__ = [
    "Base",
    "get_engine",
    "get_session",
    "campaign_session",
    "init_campaign_schema",
]
