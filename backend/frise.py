"""Frise chronologique (spec §6.10) : fusionne sur un même axe temporel les
événements, recettes, dépenses et échéances légales. Filtrable par type côté UI.

Sert de journal de bord visuel et de support de justification (procédure
contradictoire CNCCFP).
"""

from __future__ import annotations

import comptes
import echeancier
import evenements


def frise(campaign_id: str) -> list[dict]:
    items: list[dict] = []

    for e in evenements.list_evenements(campaign_id):
        items.append({
            "date": e["date_debut"],
            "type": "evenement",
            "titre": e["titre"],
            "sous_titre": e["lieu"],
            "montant": e["cout"],
            "ref_id": e["id"],
            "meta": {"type_evenement": e["type"], "nb_depenses": e["nb_depenses"]},
        })

    for r in comptes.list_recettes(campaign_id):
        items.append({
            "date": r["date"],
            "type": "recette",
            "titre": r["nom_donateur"] or "Recette",
            "sous_titre": r["type"],
            "montant": r["montant"],
            "ref_id": r["id"],
            "meta": {},
        })

    for d in comptes.list_depenses(campaign_id):
        items.append({
            "date": d["date"],
            "type": "depense",
            "titre": d["libelle"] or "Dépense",
            "sous_titre": d["fournisseur"],
            "montant": d["montant_ttc"],
            "ref_id": d["id"],
            "meta": {"is_nature": d["is_nature"]},
        })

    for ec in echeancier.echeances(campaign_id):
        items.append({
            "date": ec["date"],
            "type": "echeance",
            "titre": ec["libelle"],
            "sous_titre": ec["regle"],
            "montant": None,
            "ref_id": None,
            "meta": {"statut": ec["statut"]},
        })

    items.sort(key=lambda x: (x["date"] is None, x["date"] or ""))
    return items
