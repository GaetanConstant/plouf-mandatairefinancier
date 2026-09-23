"""Routes du cycle de validation et des demandes de pièces."""

from fastapi import APIRouter, Depends

import validation
from deps import (
    get_campaign_conn,
    get_current_user,
    get_role,
    mandataire_ou_expert,
    mandataire_requis,
    tout_role,
)

router = APIRouter(tags=["validation"], dependencies=[Depends(tout_role)])


@router.get("/validation/file")
def file_attente(campaign_id: str = Depends(get_campaign_conn),
                 _garde: str = Depends(mandataire_requis)):
    """Ce qui attend l'arbitrage du mandataire, avec l'auteur de chaque dépôt."""
    return validation.file_attente(campaign_id)


@router.get("/validation/mes-soumissions")
def mes_soumissions(current_user: dict = Depends(get_current_user),
                    campaign_id: str = Depends(get_campaign_conn)):
    """Ce que l'appelant a déposé, et où ça en est."""
    return validation.mes_soumissions(campaign_id, current_user["username"])


@router.post("/validation/{entite}/{objet_id}/valider")
def valider(entite: str, objet_id: int, current_user: dict = Depends(get_current_user),
            campaign_id: str = Depends(get_campaign_conn),
            _garde: str = Depends(mandataire_requis)):
    return validation.valider(campaign_id, entite, objet_id, current_user["username"])


@router.post("/validation/{entite}/{objet_id}/refuser")
def refuser(entite: str, objet_id: int, payload: validation.ArbitrageIn,
            current_user: dict = Depends(get_current_user),
            campaign_id: str = Depends(get_campaign_conn),
            _garde: str = Depends(mandataire_requis)):
    return validation.refuser(campaign_id, entite, objet_id, current_user["username"], payload.motif)


@router.post("/validation/{entite}/{objet_id}/resoumettre")
def resoumettre(entite: str, objet_id: int, current_user: dict = Depends(get_current_user),
                campaign_id: str = Depends(get_campaign_conn)):
    """Réservé à l'auteur de l'objet : le service vérifie la propriété."""
    return validation.resoumettre(campaign_id, entite, objet_id, current_user["username"])


# ── Demandes de pièces ───────────────────────────────────────────────────────

@router.get("/demandes-pieces")
def list_demandes(campaign_id: str = Depends(get_campaign_conn),
                  _garde: str = Depends(mandataire_ou_expert)):
    return validation.list_demandes(campaign_id)


@router.post("/demandes-pieces")
def create_demande(payload: validation.DemandePieceIn,
                   current_user: dict = Depends(get_current_user),
                   campaign_id: str = Depends(get_campaign_conn),
                   _garde: str = Depends(mandataire_ou_expert)):
    """L'expert-comptable réclame un justificatif ; le mandataire aussi, à l'équipe."""
    return validation.create_demande(campaign_id, payload, current_user["username"])


@router.post("/demandes-pieces/{demande_id}/repondre")
def repondre_demande(demande_id: int, payload: validation.ReponseDemandeIn,
                     current_user: dict = Depends(get_current_user),
                     campaign_id: str = Depends(get_campaign_conn)):
    return validation.repondre_demande(campaign_id, demande_id, payload, current_user["username"])


@router.post("/demandes-pieces/{demande_id}/clore")
def clore_demande(demande_id: int, campaign_id: str = Depends(get_campaign_conn),
                  _garde: str = Depends(mandataire_requis)):
    return validation.clore_demande(campaign_id, demande_id)
