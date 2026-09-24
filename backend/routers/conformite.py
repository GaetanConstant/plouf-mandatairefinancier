from fastapi import APIRouter, Depends

import conformite
from auth import get_current_user
from database import ROLE_EXPERT, ROLE_MANDATAIRE
from deps import get_campaign_conn, get_role, mandataire_ou_expert

router = APIRouter(tags=["conformite"], dependencies=[Depends(mandataire_ou_expert)])


@router.get("/conformite")
def get_conformite(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn),
                   role: str = Depends(get_role)):
    return conformite.run_checks(campaign_id, voir_donateurs=role in (ROLE_MANDATAIRE, ROLE_EXPERT))
