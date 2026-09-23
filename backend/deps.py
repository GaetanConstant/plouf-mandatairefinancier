"""Dépendances FastAPI partagées : campagne active et autorisation par rôle.

Le rôle est porté par le lien utilisateur↔campagne. Un même compte peut être
mandataire d'une campagne et militant sur une autre : toute vérification passe
donc par le couple (utilisateur, campagne), jamais par le seul compte.

Les gardes vivent ici et non dans le front : masquer un écran n'empêche pas
d'appeler la route.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, Request

# Ré-export pratique pour les routers.
from auth import get_current_user  # noqa: F401
from database import (  # noqa: F401
    ROLE_EQUIPE,
    ROLE_EXPERT,
    ROLE_MANDATAIRE,
    get_central_db_connection,
)


def get_active_campaign(request: Request):
    """Id de campagne lu depuis le cookie (None si aucune sélectionnée)."""
    campaign_id = request.cookies.get("campaign_id")
    return campaign_id or None


def get_campaign_conn(campaign_id: str = Depends(get_active_campaign)):
    """Exige une campagne active."""
    if not campaign_id:
        raise HTTPException(status_code=400, detail="Aucune campagne sélectionnée")
    return campaign_id


def role_sur_campagne(username: str, campaign_id: str) -> str | None:
    """Rôle de l'utilisateur sur cette campagne, None s'il n'y a pas accès."""
    with get_central_db_connection() as conn:
        ligne = conn.execute(
            "SELECT role FROM user_campaigns WHERE username = ? AND campaign_id = ?",
            (username, campaign_id),
        ).fetchone()
    return ligne[0] if ligne else None


def get_role(
    current_user: dict = Depends(get_current_user),
    campaign_id: str = Depends(get_campaign_conn),
) -> str:
    """Rôle de l'appelant sur la campagne active.

    L'administrateur de la plateforme est mandataire de fait : il doit pouvoir
    reprendre la main sur une campagne dont le mandataire a perdu son accès.
    """
    if current_user.get("role") == "admin":
        return ROLE_MANDATAIRE
    role = role_sur_campagne(current_user["username"], campaign_id)
    if role is None:
        raise HTTPException(status_code=403, detail="Vous n'avez pas accès à cette campagne")
    return role


def exiger_role(*roles_autorises: str) -> Callable:
    """Dépendance exigeant l'un des rôles donnés sur la campagne active."""

    def _garde(role: str = Depends(get_role)) -> str:
        if role not in roles_autorises:
            raise HTTPException(
                status_code=403,
                detail="Cette action est réservée au mandataire financier."
                if roles_autorises == (ROLE_MANDATAIRE,)
                else "Votre rôle sur cette campagne ne permet pas cette action.",
            )
        return role

    return _garde


# Gardes prêtes à l'emploi, pour que les routers restent lisibles.
mandataire_requis = exiger_role(ROLE_MANDATAIRE)
mandataire_ou_expert = exiger_role(ROLE_MANDATAIRE, ROLE_EXPERT)
tout_role = exiger_role(ROLE_MANDATAIRE, ROLE_EXPERT, ROLE_EQUIPE)
