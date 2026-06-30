from fastapi import APIRouter, Depends
from pydantic import BaseModel

import recus
from auth import get_current_user
from deps import get_campaign_conn

router = APIRouter(tags=["recus"])


class CarnetCreate(BaseModel):
    numero_carnet: str
    numero_formule_debut: int
    numero_formule_fin: int
    date_retrait_prefecture: str | None = None


class RecuIssue(BaseModel):
    carnet_id: int | None = None


@router.get("/carnets")
def list_carnets(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return recus.list_carnets(campaign_id)


@router.post("/carnets")
def create_carnet(carnet: CarnetCreate, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return recus.create_carnet(campaign_id, carnet.numero_carnet, carnet.numero_formule_debut,
                               carnet.numero_formule_fin, carnet.date_retrait_prefecture)


@router.get("/recus")
def list_recus(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return recus.list_recus(campaign_id)


@router.post("/recettes/{recette_id}/recu")
def issue_recu(recette_id: int, payload: RecuIssue | None = None,
               current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    carnet_id = payload.carnet_id if payload else None
    return recus.issue_recu(campaign_id, recette_id, carnet_id)


@router.post("/recus/{recu_id}/annuler")
def annuler_recu(recu_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return recus.annuler_recu(campaign_id, recu_id)
