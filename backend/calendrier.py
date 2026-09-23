"""Calendrier de campagne : le rétro-planning, reconstruit depuis les données.

Reprend la forme du document remis à la commission — un Gantt où chaque ligne
est une activité et chaque colonne une semaine — mais le construit à partir de
ce que l'application sait déjà : les jalons légaux calculés par `echeancier`,
les événements saisis et leur coût réel.

L'intérêt par rapport à un tableur tenu à la main : une activité ne peut pas
afficher un coût différent de celui du compte, puisque c'est le même chiffre.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select

import echeancier
import evenements
from db import enums

# Libellés des types d'événement, dans l'ordre d'affichage du calendrier.
GROUPES_EVENEMENT = [
    (enums.TypeEvenement.reunion_publique, "Réunions publiques"),
    (enums.TypeEvenement.meeting, "Meetings"),
    (enums.TypeEvenement.tractage, "Tractage"),
    (enums.TypeEvenement.porte_a_porte, "Porte à porte"),
    (enums.TypeEvenement.collecte, "Collectes"),
    (enums.TypeEvenement.reception, "Réceptions"),
    (enums.TypeEvenement.autre, "Autres"),
]

MOIS_COURTS = ("janv.", "févr.", "mars", "avril", "mai", "juin",
               "juil.", "août", "sept.", "oct.", "nov.", "déc.")


def _lundi(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _parse(valeur: Optional[str]) -> Optional[date]:
    return date.fromisoformat(valeur) if valeur else None


def _semaines(debut: date, fin: date) -> list[dict]:
    """Colonnes du calendrier : une par semaine, du lundi au dimanche."""
    colonnes = []
    courante = _lundi(debut)
    while courante <= fin:
        colonnes.append({
            "debut": courante,
            "fin": courante + timedelta(days=6),
            "mois": courante.month,
            "annee": courante.year,
            "numero": courante.isocalendar().week,
        })
        courante += timedelta(days=7)
    return colonnes


# Au-delà de cette longueur, une plage sans aucune activité est repliée en une
# seule colonne. En deçà, la replier ferait perdre plus en lisibilité qu'elle ne
# ferait gagner en place.
SEUIL_REPLI = 3

# Semaines conservées de part et d'autre d'une activité : une barre collée au
# bord d'un repli ne se situe plus dans le temps.
MARGE_CONTEXTE = 2


def _colonnes(semaines: list[dict], occupees: set[int]) -> list[dict]:
    """Colonnes du calendrier, plages creuses repliées.

    La période légale court sur six mois avant le scrutin, mais une campagne se
    concentre souvent sur ses dernières semaines : afficher les mois vides à la
    même échelle écrase la partie qui porte l'information.
    """
    colonnes: list[dict] = []
    i, n = 0, len(semaines)
    while i < n:
        if i in occupees:
            colonnes.append({"type": "semaine", "semaines": [i], **semaines[i]})
            i += 1
            continue

        j = i
        while j < n and j not in occupees:
            j += 1
        creux = list(range(i, j))
        if len(creux) > SEUIL_REPLI:
            colonnes.append({
                "type": "repli",
                "semaines": creux,
                "nb_semaines": len(creux),
                "debut": semaines[i]["debut"],
                "fin": semaines[j - 1]["fin"],
            })
        else:
            colonnes.extend({"type": "semaine", "semaines": [k], **semaines[k]} for k in creux)
        i = j
    return colonnes


def _entetes(colonnes: list[dict]) -> list[dict]:
    """Bandeau supérieur : un mois par groupe de semaines, un repli à part."""
    entetes: list[dict] = []
    for c in colonnes:
        if c["type"] == "repli":
            debut, fin = c["debut"], c["fin"]
            libelle = MOIS_COURTS[debut.month - 1]
            if fin.month != debut.month:
                libelle += f" → {MOIS_COURTS[fin.month - 1]}"
            entetes.append({"repli": True, "largeur": 1,
                            "libelle": libelle, "detail": f"{c['nb_semaines']} sem."})
            continue
        if entetes and not entetes[-1]["repli"] and entetes[-1].get("mois") == c["mois"] \
                and entetes[-1].get("annee") == c["annee"]:
            entetes[-1]["largeur"] += 1
        else:
            entetes.append({"repli": False, "mois": c["mois"], "annee": c["annee"],
                            "largeur": 1, "detail": None,
                            "libelle": f"{MOIS_COURTS[c['mois'] - 1]} {c['annee']}"})
    return entetes


def _positions(debut: Optional[date], fin: Optional[date], semaines: list[dict]) -> tuple[int, int]:
    """Index de première et dernière colonne couvertes (-1, -1 si hors période)."""
    if debut is None:
        return -1, -1
    fin = fin or debut
    couvertes = [i for i, s in enumerate(semaines) if s["fin"] >= debut and s["debut"] <= fin]
    return (couvertes[0], couvertes[-1]) if couvertes else (-1, -1)


def _date_scrutin(campaign_id: str) -> Optional[date]:
    """Jour du scrutin : second tour s'il est prévu, sinon premier."""
    from db.models import Election
    from db.session import campaign_session

    with campaign_session(campaign_id) as s:
        e = s.scalars(select(Election)).first()
        if not e:
            return None
        return e.date_tour2 or e.date_tour1


def donnees(campaign_id: str) -> dict:
    """Calendrier complet : bornes, colonnes hebdomadaires et lignes groupées."""
    jalons = echeancier.echeances(campaign_id)
    evts = evenements.list_evenements(campaign_id)

    dates = [_parse(j["date"]) for j in jalons if j.get("date")]
    for e in evts:
        dates += [_parse(e.get("date_debut")), _parse(e.get("date_fin"))]
    dates = [d for d in dates if d]
    if not dates:
        return {"vide": True, "semaines": [], "mois": [], "groupes": [], "total_cout": 0.0}

    # Le calendrier couvre la campagne elle-même : de son ouverture officielle
    # — le début de la période de financement — au jour du scrutin. Ce qui suit
    # relève de l'administration du compte (dépôt, clôture, fin de mandat) et
    # étirerait l'axe de plusieurs mois pour trois lignes : listé à part.
    ouverture = next((_parse(j["date"]) for j in jalons
                      if j["libelle"].startswith("Ouverture de la période")), None)
    scrutin = _date_scrutin(campaign_id)
    debut = ouverture or min(dates)
    fin = scrutin or max(dates)
    if fin < debut:
        debut, fin = min(dates), max(dates)
    semaines = _semaines(debut, fin)

    groupes: list[dict] = []

    lignes_jalons = []
    jalons_apres = []
    for j in jalons:
        d = _parse(j.get("date"))
        i, f = _positions(d, d, semaines)
        if i < 0 and d is not None:
            jalons_apres.append({"libelle": j["libelle"], "date": j["date"], "regle": j.get("regle")})
        if i >= 0:
            lignes_jalons.append({
                "libelle": j["libelle"], "detail": j.get("regle"),
                "debut": d.isoformat(), "fin": d.isoformat(),
                "colonne": i, "largeur": f - i + 1, "cout": None,
                "statut": j.get("statut"),
            })
    if lignes_jalons:
        groupes.append({"titre": "Jalons légaux", "jalon": True, "lignes": lignes_jalons})

    for type_evt, titre in GROUPES_EVENEMENT:
        lignes = []
        for e in evts:
            if e.get("type") != type_evt.value:
                continue
            d1, d2 = _parse(e.get("date_debut")), _parse(e.get("date_fin"))
            i, f = _positions(d1, d2, semaines)
            if i < 0:
                continue
            lignes.append({
                "libelle": e["titre"], "detail": e.get("lieu"),
                "debut": e["date_debut"], "fin": e.get("date_fin") or e["date_debut"],
                "colonne": i, "largeur": f - i + 1, "cout": e.get("cout") or 0.0,
                "statut": None,
            })
        if lignes:
            lignes.sort(key=lambda l: l["debut"])
            groupes.append({"titre": titre, "jalon": False, "lignes": lignes})

    # Semaines réellement couvertes par une activité : le reste peut se replier.
    occupees: set[int] = set()
    for g in groupes:
        for l in g["lignes"]:
            debut_marge = max(0, l["colonne"] - MARGE_CONTEXTE)
            fin_marge = min(len(semaines), l["colonne"] + l["largeur"] + MARGE_CONTEXTE)
            occupees.update(range(debut_marge, fin_marge))
    colonnes = _colonnes(semaines, occupees)

    # Chaque semaine pointe vers la colonne qui la porte (plusieurs semaines
    # repliées partagent la même).
    colonne_de_semaine: dict[int, int] = {}
    for index, c in enumerate(colonnes):
        for i in c["semaines"]:
            colonne_de_semaine[i] = index

    for g in groupes:
        for l in g["lignes"]:
            premiere = colonne_de_semaine[l["colonne"]]
            derniere = colonne_de_semaine[l["colonne"] + l["largeur"] - 1]
            l["colonne"], l["largeur"] = premiere, derniere - premiere + 1

    total = sum(l["cout"] or 0.0 for g in groupes for l in g["lignes"])
    return {
        "vide": False,
        "debut": debut.isoformat(),
        "fin": fin.isoformat(),
        "nb_semaines": len(semaines),
        "colonnes": [
            {**c, "debut": c["debut"].isoformat(), "fin": c["fin"].isoformat()}
            for c in colonnes
        ],
        "mois": _entetes(colonnes),
        "groupes": groupes,
        "jalons_apres": jalons_apres,
        "total_cout": total,
        "nb_evenements": sum(len(g["lignes"]) for g in groupes if not g["jalon"]),
    }


# ── Rendus ───────────────────────────────────────────────────────────────────

_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "templates", "calendrier_campagne.html")


def _jolie_date(iso: Optional[str]) -> str:
    if not iso:
        return ""
    d = date.fromisoformat(iso)
    return f"{d.day} {MOIS_COURTS[d.month - 1]} {d.year}"


def export_pdf(campaign_id: str) -> bytes:
    """Calendrier en PDF paysage, joignable au dossier de dépôt."""
    # macOS : Pango/GLib viennent de Homebrew, absents des chemins par défaut.
    # Même contournement que conventions/generate_convention.py. Sans effet sous
    # Linux, où l'image Docker installe les bibliothèques système.
    os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")

    from jinja2 import Template
    from weasyprint import HTML

    from db.models import Election
    from db.session import campaign_session

    donnees_calendrier = donnees(campaign_id)
    if donnees_calendrier["vide"]:
        raise HTTPException(status_code=409,
                            detail="Aucune date à représenter : ni jalon ni événement.")

    with campaign_session(campaign_id) as s:
        election = s.scalars(select(Election)).first()
        titre = (election.libelle if election else None) or "Campagne"

    html = Template(Path(_TEMPLATE).read_text(encoding="utf-8")).render(
        titre=titre,
        debut=_jolie_date(donnees_calendrier["debut"]),
        fin=_jolie_date(donnees_calendrier["fin"]),
        edite_le=date.today().strftime("%d/%m/%Y"),
        **{k: donnees_calendrier[k] for k in
           ("colonnes", "mois", "groupes", "jalons_apres", "total_cout",
            "nb_evenements", "nb_semaines")},
    )
    return HTML(string=html).write_pdf()
