import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

import maincourante
from auth import get_current_user
from deps import get_campaign_conn

router = APIRouter(tags=["main-courante"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/main-courante")
def get_main_courante(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return maincourante.journal(campaign_id)


@router.get("/main-courante/export")
def export_main_courante(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    xlsx = maincourante.export_annexe8_xlsx(campaign_id)
    filename = f"main_courante_annexe8_{campaign_id}.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx),
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
