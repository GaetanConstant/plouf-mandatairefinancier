from fastapi import APIRouter, Depends

import comptes
from auth import get_current_user
from deps import get_campaign_conn
from models import Recette, Depense, SpendingStats

router = APIRouter(tags=["comptes"])


@router.get("/stats", response_model=SpendingStats)
def get_stats(campaign_id: str = Depends(get_campaign_conn)):
    return SpendingStats(**comptes.compute_stats(campaign_id))


@router.post("/recettes")
def create_recette(recette: Recette, campaign_id: str = Depends(get_campaign_conn)):
    return comptes.create_recette(campaign_id, recette)


@router.put("/recettes/{recette_id}")
def update_recette(recette_id: int, update: Recette, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return comptes.update_recette(campaign_id, recette_id, update)


@router.get("/recettes")
def list_recettes(campaign_id: str = Depends(get_campaign_conn)):
    return comptes.list_recettes(campaign_id)


@router.post("/depenses")
def create_depense(depense: Depense, campaign_id: str = Depends(get_campaign_conn)):
    return comptes.create_depense(campaign_id, depense)


@router.put("/depenses/{depense_id}")
def update_depense(depense_id: int, update: Depense, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return comptes.update_depense(campaign_id, depense_id, update)


@router.get("/depenses")
def list_depenses(campaign_id: str = Depends(get_campaign_conn)):
    return comptes.list_depenses(campaign_id)


@router.get("/fournisseurs")
def list_fournisseurs(campaign_id: str = Depends(get_campaign_conn)):
    return comptes.list_fournisseurs(campaign_id)
