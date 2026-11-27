"""Routes des indemnités kilométriques."""

from fastapi import APIRouter, Depends

import indemnites_km
from auth import get_current_user
from deps import get_campaign_conn, mandataire_requis

router = APIRouter(tags=["indemnites-km"], dependencies=[Depends(mandataire_requis)])


@router.get("/indemnites-km/bareme")
def bareme() -> list[dict]:
    return indemnites_km.bareme()


@router.post("/indemnites-km")
def creer(payload: indemnites_km.IndemniteKmIn,
          campaign_id: str = Depends(get_campaign_conn),
          current_user: dict = Depends(get_current_user)) -> dict:
    """Crée la dépense D1 et son état de frais kilométriques signé du visa."""
    return indemnites_km.creer(campaign_id, payload, current_user["username"])
