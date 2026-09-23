import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

import mutualisation
import livre_comptes
from auth import get_current_user
from deps import get_campaign_conn, mandataire_requis

router = APIRouter(tags=["mutualisation"], dependencies=[Depends(mandataire_requis)])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/parties-externes")
def list_parties(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return mutualisation.list_parties(campaign_id)


@router.post("/parties-externes")
def create_partie(payload: mutualisation.PartieExterneIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return mutualisation.create_partie(campaign_id, payload)


@router.get("/mutualisations")
def list_mutualisations(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return mutualisation.list_mutualisees(campaign_id)


@router.post("/mutualisations")
def create_mutualisation(payload: mutualisation.MutualiseeIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return mutualisation.create_mutualisee(campaign_id, payload)


@router.delete("/mutualisations/{mut_id}")
def delete_mutualisation(mut_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return mutualisation.delete_mutualisee(campaign_id, mut_id)


@router.get("/mutualisations/{mut_id}/convention")
def convention_pdf(mut_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    pdf = mutualisation.convention_pdf(campaign_id, mut_id)
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=convention_{mut_id}.pdf"})


@router.get("/mutualisations/export")
def export_mutualisations(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    xlsx = mutualisation.export_etat_xlsx(campaign_id)
    return StreamingResponse(io.BytesIO(xlsx), media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f"attachment; filename=etat_depenses_mutualisees_{campaign_id}.xlsx"})


@router.get("/livre-comptes/export")
def export_livre_comptes(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    xlsx = livre_comptes.generate_xlsx(campaign_id)
    return StreamingResponse(io.BytesIO(xlsx), media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f"attachment; filename=livre_comptes_{campaign_id}.xlsx"})
