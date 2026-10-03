"""Routes des relevés bancaires et du rapprochement."""

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

import releves
from deps import (
    get_campaign_conn,
    get_current_user,
    mandataire_ou_expert,
    mandataire_requis,
)

router = APIRouter(tags=["releves"], dependencies=[Depends(mandataire_ou_expert)])


class TexteIn(BaseModel):
    texte: str


@router.get("/releves")
def list_releves(campaign_id: str = Depends(get_campaign_conn)):
    return releves.list_releves(campaign_id)


@router.post("/releves/lire-csv")
async def lire_csv(file: UploadFile = File(...), campaign_id: str = Depends(get_campaign_conn),
                   _garde: str = Depends(mandataire_requis)):
    """Aperçu des transactions d'un CSV, sans rien enregistrer.

    L'import se fait en deux temps : on lit, on relit à l'écran, puis on valide.
    Un fichier bancaire mal découpé ne doit pas entrer directement au compte.
    """
    return {"transactions": releves.lire_csv(await file.read())}


@router.post("/releves/lire-texte")
def lire_texte(payload: TexteIn, campaign_id: str = Depends(get_campaign_conn),
               _garde: str = Depends(mandataire_requis)):
    """Aperçu depuis un copier-coller. Même principe que le CSV."""
    return {"transactions": releves.lire_texte(payload.texte)}


@router.post("/releves/lire-image")
async def lire_image(file: UploadFile = File(...), campaign_id: str = Depends(get_campaign_conn),
                     _garde: str = Depends(mandataire_requis)):
    """Aperçu depuis un PDF ou une photo de relevé, via OCR.

    La reconnaissance se trompe : le résultat est une proposition à corriger,
    jamais un import direct.
    """
    from ocr_utils import extract_text_from_file

    texte = extract_text_from_file(await file.read(), file.filename or "releve.pdf")
    return {"transactions": releves.lire_texte(texte), "texte_ocr": texte}


@router.post("/releves")
def create_releve(payload: releves.ReleveIn, current_user: dict = Depends(get_current_user),
                  campaign_id: str = Depends(get_campaign_conn),
                  _garde: str = Depends(mandataire_requis)):
    return releves.create_releve(campaign_id, payload, current_user["username"])


@router.delete("/releves/{releve_id}")
def delete_releve(releve_id: int, campaign_id: str = Depends(get_campaign_conn),
                  _garde: str = Depends(mandataire_requis)):
    return releves.delete_releve(campaign_id, releve_id)


@router.post("/releves/{releve_id}/transactions")
def ajouter_transaction(releve_id: int, payload: releves.TransactionIn,
                        campaign_id: str = Depends(get_campaign_conn),
                        _garde: str = Depends(mandataire_requis)):
    """Ajoute une ligne saisie à la main sur un relevé existant."""
    return releves.ajouter_transaction(campaign_id, releve_id, payload)


@router.delete("/transactions/{transaction_id}")
def supprimer_transaction(transaction_id: int,
                          campaign_id: str = Depends(get_campaign_conn),
                          _garde: str = Depends(mandataire_requis)):
    return releves.supprimer_transaction(campaign_id, transaction_id)


@router.post("/releves/{releve_id}/piece")
def attacher_piece(releve_id: int, payload: releves.PieceReleveIn,
                   current_user: dict = Depends(get_current_user),
                   campaign_id: str = Depends(get_campaign_conn),
                   _garde: str = Depends(mandataire_requis)):
    """Rattache le relevé scanné, quand les lignes ont été saisies à la main."""
    return releves.attacher_piece(campaign_id, releve_id, payload.fichier,
                                  current_user["username"])


@router.get("/rapprochement/depenses")
def depenses_a_rapprocher(campaign_id: str = Depends(get_campaign_conn)):
    """Dépenses qu'il reste à régler, avec ce qui a déjà été imputé."""
    return releves.depenses_a_rapprocher(campaign_id)


@router.post("/transactions/{transaction_id}/imputations")
def imputer(transaction_id: int, payload: releves.ImputationIn,
            campaign_id: str = Depends(get_campaign_conn),
            _garde: str = Depends(mandataire_requis)):
    return releves.imputer(campaign_id, transaction_id, payload)


@router.get("/rapprochement/recettes")
def recettes_a_rapprocher(campaign_id: str = Depends(get_campaign_conn)):
    """Recettes dont le compte ne porte pas encore la trace complète."""
    return releves.recettes_a_rapprocher(campaign_id)


@router.post("/transactions/{transaction_id}/imputations-recettes")
def imputer_recette(transaction_id: int, payload: releves.ImputationRecetteIn,
                    campaign_id: str = Depends(get_campaign_conn),
                    _garde: str = Depends(mandataire_requis)):
    return releves.imputer_recette(campaign_id, transaction_id, payload)


@router.delete("/imputations-recettes/{imputation_id}")
def desimputer_recette(imputation_id: int, campaign_id: str = Depends(get_campaign_conn),
                       _garde: str = Depends(mandataire_requis)):
    return releves.desimputer_recette(campaign_id, imputation_id)


@router.delete("/imputations/{imputation_id}")
def desimputer(imputation_id: int, campaign_id: str = Depends(get_campaign_conn),
               _garde: str = Depends(mandataire_requis)):
    return releves.desimputer(campaign_id, imputation_id)
