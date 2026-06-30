import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import depot
from auth import get_current_user
from deps import get_campaign_conn

router = APIRouter(tags=["depot"])


class DocumentUpdate(BaseModel):
    enveloppe: str | None = None
    type: str | None = None


@router.get("/documents")
def list_documents(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return depot.list_documents(campaign_id)


@router.put("/documents/{doc_id}")
def update_document(doc_id: int, payload: DocumentUpdate, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return depot.set_document(campaign_id, doc_id, payload.enveloppe, payload.type)


@router.get("/depot")
def get_depot(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return depot.get_depot(campaign_id)


@router.get("/depot/export")
def export_depot(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    pdf = depot.export_bordereau_pdf(campaign_id)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=bordereau_depot_{campaign_id}.pdf"},
    )
