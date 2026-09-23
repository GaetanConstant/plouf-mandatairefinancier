import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

import evenements
import echeancier
import frise
import rapport
from auth import get_current_user
from deps import get_campaign_conn

router = APIRouter(tags=["pilotage"])


# --- Événements + liaison n-n ---

@router.get("/evenements")
def list_evenements(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.list_evenements(campaign_id)


@router.post("/evenements")
def create_evenement(payload: evenements.EvenementIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.create_evenement(campaign_id, payload)


@router.get("/evenements/{evenement_id}")
def detail_evenement(evenement_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.detail_evenement(campaign_id, evenement_id)


@router.put("/evenements/{evenement_id}")
def update_evenement(evenement_id: int, payload: evenements.EvenementIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.update_evenement(campaign_id, evenement_id, payload)


@router.delete("/evenements/{evenement_id}")
def delete_evenement(evenement_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.delete_evenement(campaign_id, evenement_id)


@router.post("/evenements/{evenement_id}/depenses")
def link_depense(evenement_id: int, payload: evenements.LiaisonIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.link_depense(campaign_id, evenement_id, payload)


@router.get("/evenements/{evenement_id}/documents")
def list_documents_evenement(evenement_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.list_documents_evenement(campaign_id, evenement_id)


@router.post("/evenements/{evenement_id}/documents")
def link_document(evenement_id: int, payload: evenements.DocumentEvenementIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.link_document(campaign_id, evenement_id, payload)


@router.delete("/evenements/{evenement_id}/documents/{doc_id}")
def unlink_document(evenement_id: int, doc_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.unlink_document(campaign_id, evenement_id, doc_id)


@router.delete("/evenements/{evenement_id}/depenses/{depense_id}")
def unlink_depense(evenement_id: int, depense_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.unlink_depense(campaign_id, evenement_id, depense_id)


# --- Échéancier / Frise / Rapport ---

@router.get("/echeancier")
def get_echeancier(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return echeancier.echeances(campaign_id)


@router.get("/frise")
def get_frise(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return frise.frise(campaign_id)


@router.get("/rapport")
def get_rapport(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    pdf = rapport.generate(campaign_id)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=rapport_campagne_{campaign_id}.pdf"},
    )
