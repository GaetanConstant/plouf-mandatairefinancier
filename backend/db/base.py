"""Base déclarative SQLAlchemy partagée par tous les modèles de campagne."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe de base pour toutes les tables du modèle métier d'une campagne."""

    pass
