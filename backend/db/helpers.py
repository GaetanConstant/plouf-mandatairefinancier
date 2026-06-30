"""Helpers partagés par la couche service (anti-duplication)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from db.models import Election


def election_id(session) -> Optional[int]:
    """Id de l'unique Election de la campagne (None si pas encore créée)."""
    e = session.scalars(select(Election)).first()
    return e.id if e else None


def fmt_date(d) -> Optional[str]:
    """Formate une date en 'YYYY-MM-DD' (None -> None)."""
    if d is None:
        return None
    return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
