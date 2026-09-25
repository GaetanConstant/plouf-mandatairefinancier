import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import completude
import depot
import devolution
import export_cnccfp
from auth import get_current_user
from deps import get_campaign_conn, mandataire_ou_expert, mandataire_requis

router = APIRouter(tags=["depot"], dependencies=[Depends(mandataire_ou_expert)])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class DocumentUpdate(BaseModel):
    enveloppe: str | None = None
    type: str | None = None


@router.get("/documents")
def list_documents(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return depot.list_documents(campaign_id)


@router.put("/documents/{doc_id}")
def update_document(doc_id: int, payload: DocumentUpdate, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_requis)):
    return depot.set_document(campaign_id, doc_id, payload.enveloppe, payload.type)


def _exiger_dossier_complet(campaign_id: str) -> None:
    """Refuse l'export d'une pièce officielle tant qu'il manque des données.

    Le dossier part à la CNCCFP : un bordereau exporté avec un expert-comptable
    vide devrait être refait. L'erreur porte la liste des manques pour que
    l'écran puisse l'afficher telle quelle.
    """
    etat = completude.evaluer(campaign_id)
    if not etat["complet"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Dossier incomplet : export impossible.",
                "pct": etat["pct"],
                "manquants": etat["manquants"],
            },
        )


@router.get("/depot")
def get_depot(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return depot.get_depot(campaign_id)


@router.get("/depot/export")
def export_depot(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_requis)):
    _exiger_dossier_complet(campaign_id)
    pdf = depot.export_bordereau_pdf(campaign_id)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=bordereau_depot_{campaign_id}.pdf"},
    )


@router.get("/depot/dossier-zip")
def export_dossier_zip(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_requis)):
    """Dossier complet : bordereau + contenu des enveloppes, fichiers d'origine."""
    _exiger_dossier_complet(campaign_id)
    archive = depot.export_dossier_zip(campaign_id)
    return StreamingResponse(
        io.BytesIO(archive),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=dossier_depot_{campaign_id}.zip"},
    )


@router.get("/depot/dossier-pdf")
def export_dossier_pdf(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_requis)):
    """Dossier complet en un seul PDF paginé, pour l'impression ou l'envoi d'un bloc."""
    _exiger_dossier_complet(campaign_id)
    pdf = depot.export_dossier_pdf(campaign_id)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=dossier_depot_{campaign_id}.pdf"},
    )


@router.get("/depot/export-cnccfp")
def export_cnccfp_xlsx(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn), _garde: str = Depends(mandataire_requis)):
    _exiger_dossier_complet(campaign_id)
    xlsx = export_cnccfp.generate_xlsx(campaign_id)
    return StreamingResponse(
        io.BytesIO(xlsx),
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f"attachment; filename=compte_campagne_format_cnccfp_{campaign_id}.xlsx"},
    )


# ── Dévolution de l'excédent ─────────────────────────────────────────────────

@router.get("/devolution")
def etat_devolution(campaign_id: str = Depends(get_campaign_conn)):
    """Excédent du compte, son origine, et la dévolution qu'il implique."""
    return devolution.etat(campaign_id)


@router.put("/devolution")
def enregistrer_devolution(payload: devolution.DevolutionIn,
                           campaign_id: str = Depends(get_campaign_conn),
                           _garde: str = Depends(mandataire_requis)):
    return devolution.enregistrer(campaign_id, payload)


@router.delete("/devolution")
def supprimer_devolution(campaign_id: str = Depends(get_campaign_conn),
                         _garde: str = Depends(mandataire_requis)):
    return devolution.supprimer(campaign_id)
