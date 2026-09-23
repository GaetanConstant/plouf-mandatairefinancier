from fastapi import APIRouter, Depends

import completude
import identite
from auth import get_current_user
from deps import get_campaign_conn, mandataire_requis

router = APIRouter(prefix="/identite", tags=["identite"], dependencies=[Depends(mandataire_requis)])


@router.get("")
def get_identite(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.get_identite(campaign_id)


@router.put("/election")
def put_election(payload: identite.ElectionIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.save_election(campaign_id, payload)


@router.put("/candidat")
def put_candidat(payload: identite.CandidatIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.save_candidat(campaign_id, payload)


@router.put("/mandataire")
def put_mandataire(payload: identite.MandataireIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.save_mandataire(campaign_id, payload)


@router.put("/expert-comptable")
def put_expert(payload: identite.ExpertComptableIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.save_expert(campaign_id, payload)


@router.put("/compte-bancaire")
def put_compte(payload: identite.CompteBancaireIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.save_compte(campaign_id, payload)


@router.get("/completude")
def get_completude(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    """État de remplissage du dossier, section par section."""
    return completude.evaluer(campaign_id)
