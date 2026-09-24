import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

import maincourante
from auth import get_current_user
from database import ROLE_EXPERT, ROLE_MANDATAIRE
from deps import get_campaign_conn, get_role, lecture_donateurs, mandataire_ou_expert

router = APIRouter(tags=["main-courante"], dependencies=[Depends(mandataire_ou_expert)])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/main-courante")
def get_main_courante(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn),
                      role: str = Depends(get_role)):
    return maincourante.journal(campaign_id, voir_donateurs=role in (ROLE_MANDATAIRE, ROLE_EXPERT))


@router.get("/main-courante/export")
def export_main_courante(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn),
                         _garde: str = Depends(lecture_donateurs)):
    xlsx = maincourante.export_annexe8_xlsx(campaign_id)
    filename = f"main_courante_annexe8_{campaign_id}.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx),
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
