"""Dépendances FastAPI partagées par les routers."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

# Ré-export pratique pour les routers.
from auth import get_current_user  # noqa: F401


def get_active_campaign(request: Request):
    """Id de campagne lu depuis le cookie (None si aucune sélectionnée)."""
    campaign_id = request.cookies.get("campaign_id")
    return campaign_id or None


def get_campaign_conn(campaign_id: str = Depends(get_active_campaign)):
    """Exige une campagne active."""
    if not campaign_id:
        raise HTTPException(status_code=400, detail="Aucune campagne sélectionnée")
    return campaign_id
