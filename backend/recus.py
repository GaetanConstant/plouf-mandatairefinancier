"""Service des carnets de reçus-dons et des reçus numérotés (spec Bloc C / §5).

- Un carnet retiré en préfecture couvre une plage de numéros de formule.
- Chaque don donne lieu à un reçu numéroté séquentiellement dans un carnet.
- Statuts d'une formule : délivré, annulé, non utilisé (à restituer).
"""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select

from db.models import CarnetRecus, Donateur, Election, Recette, RecuDon
from db.session import campaign_session, ensure_campaign_db
from db import enums


def _election_id(s) -> int | None:
    el = s.scalars(select(Election)).first()
    return el.id if el else None


def _fmt(d) -> str | None:
    if d is None:
        return None
    return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)


# ── Carnets ──────────────────────────────────────────────────────────────────

def create_carnet(campaign_id: str, numero_carnet: str, debut: int, fin: int,
                   date_retrait: str | None = None) -> dict:
    ensure_campaign_db(campaign_id)
    if fin < debut:
        raise HTTPException(status_code=400, detail="Le numéro de fin doit être ≥ au numéro de début.")
    with campaign_session(campaign_id) as s:
        carnet = CarnetRecus(
            election_id=_election_id(s),
            numero_carnet=numero_carnet,
            numero_formule_debut=debut,
            numero_formule_fin=fin,
            date_retrait_prefecture=date.fromisoformat(date_retrait) if date_retrait else None,
        )
        s.add(carnet)
        s.flush()
        return {"id": carnet.id, "message": "Carnet créé"}


def _carnet_stats(s, carnet: CarnetRecus) -> dict:
    total = carnet.numero_formule_fin - carnet.numero_formule_debut + 1
    delivres = s.scalar(
        select(func.count()).where(RecuDon.carnet_id == carnet.id,
                                    RecuDon.statut == enums.StatutRecuDon.delivre)
    ) or 0
    annules = s.scalar(
        select(func.count()).where(RecuDon.carnet_id == carnet.id,
                                   RecuDon.statut == enums.StatutRecuDon.annule)
    ) or 0
    consommes = delivres + annules
    return {
        "id": carnet.id,
        "numero_carnet": carnet.numero_carnet,
        "numero_formule_debut": carnet.numero_formule_debut,
        "numero_formule_fin": carnet.numero_formule_fin,
        "date_retrait_prefecture": _fmt(carnet.date_retrait_prefecture),
        "nb_total": total,
        "nb_delivres": delivres,
        "nb_annules": annules,
        "nb_restants": total - consommes,  # formules non utilisées (à restituer en fin de campagne)
    }


def list_carnets(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        carnets = s.scalars(select(CarnetRecus).order_by(CarnetRecus.numero_formule_debut)).all()
        return [_carnet_stats(s, c) for c in carnets]


# ── Reçus-dons ───────────────────────────────────────────────────────────────

def _next_formule(s, carnet: CarnetRecus) -> int:
    """Prochain numéro de formule séquentiel disponible dans le carnet."""
    max_used = s.scalar(
        select(func.max(RecuDon.numero_formule)).where(RecuDon.carnet_id == carnet.id)
    )
    nxt = carnet.numero_formule_debut if max_used is None else max_used + 1
    if nxt > carnet.numero_formule_fin:
        raise HTTPException(status_code=400,
                            detail=f"Carnet {carnet.numero_carnet} épuisé (dernière formule {carnet.numero_formule_fin}).")
    return nxt


def issue_recu(campaign_id: str, recette_id: int, carnet_id: int | None = None) -> dict:
    """Délivre un reçu numéroté pour une recette (don), depuis un carnet."""
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        recette = s.get(Recette, recette_id)
        if not recette:
            raise HTTPException(status_code=404, detail="Recette introuvable")
        if recette.categorie != enums.CategorieRecette.don:
            raise HTTPException(status_code=400, detail="Un reçu-don ne concerne que les dons.")

        # Réutilise un reçu existant non annulé pour cette recette.
        existant = s.scalars(
            select(RecuDon).where(RecuDon.recette_id == recette_id,
                                  RecuDon.statut != enums.StatutRecuDon.annule)
        ).first()
        if existant:
            return {"id": existant.id, "numero_formule": existant.numero_formule,
                    "carnet_id": existant.carnet_id, "message": "Reçu déjà délivré"}

        if carnet_id is not None:
            carnet = s.get(CarnetRecus, carnet_id)
            if not carnet:
                raise HTTPException(status_code=404, detail="Carnet introuvable")
        else:
            # Premier carnet ayant encore des formules disponibles.
            carnet = None
            for c in s.scalars(select(CarnetRecus).order_by(CarnetRecus.numero_formule_debut)).all():
                max_used = s.scalar(select(func.max(RecuDon.numero_formule)).where(RecuDon.carnet_id == c.id))
                nxt = c.numero_formule_debut if max_used is None else max_used + 1
                if nxt <= c.numero_formule_fin:
                    carnet = c
                    break
            if carnet is None:
                raise HTTPException(status_code=400,
                                    detail="Aucun carnet disponible (créez un carnet ou ajoutez des formules).")

        numero = _next_formule(s, carnet)
        # Avantage fiscal : éligible si versement scriptural (pas en espèces).
        eligible = recette.mode != enums.ModePaiement.especes
        recu = RecuDon(
            numero_formule=numero,
            carnet_id=carnet.id,
            recette_id=recette.id,
            montant=recette.montant,
            date=recette.date_versement,
            statut=enums.StatutRecuDon.delivre,
            avantage_fiscal_eligible=eligible,
        )
        s.add(recu)
        recette.recu_genere = True
        s.flush()
        return {"id": recu.id, "numero_formule": numero, "carnet_id": carnet.id,
                "message": "Reçu délivré"}


def annuler_recu(campaign_id: str, recu_id: int) -> dict:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        recu = s.get(RecuDon, recu_id)
        if not recu:
            raise HTTPException(status_code=404, detail="Reçu introuvable")
        recu.statut = enums.StatutRecuDon.annule
        return {"message": "Reçu annulé"}


def list_recus(campaign_id: str) -> list[dict]:
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        recus = s.scalars(select(RecuDon).order_by(RecuDon.carnet_id, RecuDon.numero_formule)).all()
        out = []
        for r in recus:
            recette = s.get(Recette, r.recette_id) if r.recette_id else None
            donateur = s.get(Donateur, recette.donateur_id) if recette and recette.donateur_id else None
            out.append({
                "id": r.id,
                "numero_formule": r.numero_formule,
                "carnet_id": r.carnet_id,
                "recette_id": r.recette_id,
                "nom_donateur": donateur.nom if donateur else None,
                "montant": r.montant,
                "date": _fmt(r.date),
                "statut": r.statut.value,
                "avantage_fiscal_eligible": r.avantage_fiscal_eligible,
            })
        return out


def numero_recu_pour_recette(campaign_id: str, recette_id: int) -> str | None:
    """Référence affichable du reçu d'une recette (carnet/formule), si délivré."""
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        recu = s.scalars(
            select(RecuDon).where(RecuDon.recette_id == recette_id,
                                  RecuDon.statut == enums.StatutRecuDon.delivre)
        ).first()
        if not recu:
            return None
        carnet = s.get(CarnetRecus, recu.carnet_id)
        prefix = f"{carnet.numero_carnet}-" if carnet else ""
        return f"{prefix}{recu.numero_formule}"
