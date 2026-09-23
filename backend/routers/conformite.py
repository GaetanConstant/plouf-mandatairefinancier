from fastapi import APIRouter, Depends

import conformite
from auth import get_current_user
from deps import get_campaign_conn, mandataire_ou_expert

router = APIRouter(tags=["conformite"], dependencies=[Depends(mandataire_ou_expert)])


@router.get("/conformite")
def get_conformite(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return conformite.run_checks(campaign_id)
