"""Routes des notes de frais."""

from fastapi import APIRouter, Depends, Response

import notes_frais
from auth import get_current_user
from deps import get_campaign_conn, mandataire_ou_expert, mandataire_requis

router = APIRouter(tags=["notes-de-frais"], dependencies=[Depends(mandataire_ou_expert)])


@router.get("/notes-frais")
def list_notes(campaign_id: str = Depends(get_campaign_conn)):
    return notes_frais.list_notes(campaign_id)


@router.post("/notes-frais")
def create_note(payload: notes_frais.NoteFraisIn,
                campaign_id: str = Depends(get_campaign_conn),
                _garde: str = Depends(mandataire_requis)):
    return notes_frais.create_note(campaign_id, payload)


@router.delete("/notes-frais/{note_id}")
def delete_note(note_id: int, campaign_id: str = Depends(get_campaign_conn),
                _garde: str = Depends(mandataire_requis)):
    return notes_frais.delete_note(campaign_id, note_id)


@router.post("/notes-frais/{note_id}/piece")
def attacher_piece(note_id: int, payload: notes_frais.PieceNoteIn,
                   current_user: dict = Depends(get_current_user),
                   campaign_id: str = Depends(get_campaign_conn),
                   _garde: str = Depends(mandataire_requis)):
    return notes_frais.attacher_piece(campaign_id, note_id, payload.fichier,
                                      current_user["username"])


@router.get("/notes-frais/{note_id}/pdf")
def export_pdf(note_id: int, campaign_id: str = Depends(get_campaign_conn)):
    """La note à imprimer et faire signer."""
    return Response(
        content=notes_frais.export_pdf(campaign_id, note_id),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="note-de-frais-{note_id}.pdf"'},
    )
