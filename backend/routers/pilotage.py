import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

import calendrier
import evenements
import echeancier
import frise
import rapport
from auth import get_current_user
from deps import get_campaign_conn, get_role, mandataire_ou_expert, mandataire_requis, tout_role

router = APIRouter(tags=["pilotage"], dependencies=[Depends(tout_role)])


# --- Événements + liaison n-n ---

@router.get("/evenements")
def list_evenements(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.list_evenements(campaign_id)


@router.post("/evenements")
def create_evenement(payload: evenements.EvenementIn, current_user: dict = Depends(get_current_user),
                     campaign_id: str = Depends(get_campaign_conn), role: str = Depends(get_role)):
    return evenements.create_evenement(campaign_id, payload, current_user["username"], role)


@router.get("/evenements/{evenement_id}")
def detail_evenement(evenement_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.detail_evenement(campaign_id, evenement_id)


@router.put("/evenements/{evenement_id}")
def update_evenement(evenement_id: int, payload: evenements.EvenementIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_requis)):
    return evenements.update_evenement(campaign_id, evenement_id, payload)


@router.delete("/evenements/{evenement_id}")
def delete_evenement(evenement_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_requis)):
    return evenements.delete_evenement(campaign_id, evenement_id)


@router.post("/evenements/{evenement_id}/depenses")
def link_depense(evenement_id: int, payload: evenements.LiaisonIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_requis)):
    return evenements.link_depense(campaign_id, evenement_id, payload)


@router.get("/calendrier")
def get_calendrier(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    """Rétro-planning de la campagne, de son ouverture au jour du scrutin."""
    return calendrier.donnees(campaign_id)


@router.get("/calendrier/export-pdf")
def export_calendrier_pdf(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_ou_expert)):
    pdf = calendrier.export_pdf(campaign_id)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=calendrier_campagne_{campaign_id}.pdf"},
    )


@router.get("/evenements/{evenement_id}/documents")
def list_documents_evenement(evenement_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return evenements.list_documents_evenement(campaign_id, evenement_id)


@router.post("/evenements/{evenement_id}/documents")
def link_document(evenement_id: int, payload: evenements.DocumentEvenementIn,
                  current_user: dict = Depends(get_current_user),
                  campaign_id: str = Depends(get_campaign_conn), role: str = Depends(get_role)):
    return evenements.link_document(campaign_id, evenement_id, payload, current_user["username"], role)


@router.delete("/evenements/{evenement_id}/documents/{doc_id}")
def unlink_document(evenement_id: int, doc_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_requis)):
    return evenements.unlink_document(campaign_id, evenement_id, doc_id)


@router.delete("/evenements/{evenement_id}/depenses/{depense_id}")
def unlink_depense(evenement_id: int, depense_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_requis)):
    return evenements.unlink_depense(campaign_id, evenement_id, depense_id)


# --- Échéancier / Frise / Rapport ---

@router.get("/echeancier")
def get_echeancier(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_ou_expert)):
    return echeancier.echeances(campaign_id)


@router.get("/frise")
def get_frise(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_ou_expert)):
    return frise.frise(campaign_id)


@router.get("/rapport")
def get_rapport(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_ou_expert)):
    pdf = rapport.generate(campaign_id)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=rapport_campagne_{campaign_id}.pdf"},
    )
