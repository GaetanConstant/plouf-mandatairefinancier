from fastapi import APIRouter, Depends

import annexes
import concours
from auth import get_current_user
from deps import get_campaign_conn, mandataire_requis

router = APIRouter(tags=["annexes-cnccfp"], dependencies=[Depends(mandataire_requis)])


@router.get("/colistiers")
def list_colistiers(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return annexes.list_colistiers(campaign_id)


@router.post("/colistiers")
def create_colistier(payload: annexes.ColistierIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return annexes.create_colistier(campaign_id, payload)


@router.delete("/colistiers/{colistier_id}")
def delete_colistier(colistier_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return annexes.delete_colistier(campaign_id, colistier_id)


@router.get("/equipe")
def list_equipe(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return annexes.list_equipe(campaign_id)


@router.post("/equipe")
def create_membre(payload: annexes.MembreEquipeIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return annexes.create_membre(campaign_id, payload)


@router.delete("/equipe/{membre_id}")
def delete_membre(membre_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return annexes.delete_membre(campaign_id, membre_id)


@router.get("/emprunts")
def list_emprunts(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return annexes.list_emprunts(campaign_id)


@router.post("/emprunts")
def create_emprunt(payload: annexes.EmpruntIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return annexes.create_emprunt(campaign_id, payload)


@router.delete("/emprunts/{emprunt_id}")
def delete_emprunt(emprunt_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return annexes.delete_emprunt(campaign_id, emprunt_id)


# ── Concours en nature (annexes 4 et 4.1) ────────────────────────────────────

@router.get("/concours-nature")
def list_concours(campaign_id: str = Depends(get_campaign_conn)):
    return concours.list_concours(campaign_id)


@router.get("/concours-nature/synthese")
def synthese_concours(campaign_id: str = Depends(get_campaign_conn)):
    """Annexe 4 : totaux par origine du concours."""
    return concours.synthese(campaign_id)


@router.post("/concours-nature")
def create_concours(payload: concours.ConcoursIn,
                    current_user: dict = Depends(get_current_user),
                    campaign_id: str = Depends(get_campaign_conn)):
    return concours.create_concours(campaign_id, payload, current_user["username"])


@router.put("/concours-nature/{concours_id}")
def update_concours(concours_id: int, payload: concours.ConcoursIn,
                    campaign_id: str = Depends(get_campaign_conn)):
    return concours.update_concours(campaign_id, concours_id, payload)


@router.delete("/concours-nature/{concours_id}")
def delete_concours(concours_id: int, campaign_id: str = Depends(get_campaign_conn)):
    return concours.delete_concours(campaign_id, concours_id)
