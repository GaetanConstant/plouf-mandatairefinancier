"""Complétude administrative du dossier de dépôt.

À distinguer du moteur de `conformite` : celui-ci vérifie des **règles** (dons
en espèces, plafonds, reçus), celui-là constate des **champs vides**. Un dossier
peut être parfaitement conforme et pourtant impossible à déposer parce que
l'expert-comptable n'est pas renseigné.

Le résultat alimente trois usages : la barre du tableau de bord, le détail par
section de l'écran Identité, et le refus d'export du dossier officiel.
"""

from __future__ import annotations

from typing import Callable, Optional

from sqlalchemy import select

from db.models import (
    Candidat,
    Colistier,
    CompteBancaire,
    Election,
    ExpertComptable,
    Mandataire,
)
from db.session import campaign_session, ensure_campaign_db


# Champs exigés pour un dépôt, par section : (attribut, libellé affiché).
# Les champs facultatifs (nom d'usage, libellé de compte, second tour…) n'y
# figurent pas : ils ne doivent pas faire baisser le score.
CHAMPS_ELECTION = [
    ("type", "Type de scrutin"),
    ("libelle", "Libellé"),
    ("circonscription", "Circonscription"),
    ("nuance_politique", "Nuance politique / Parti"),
    ("date_tour1", "Date du 1er tour"),
    ("plafond_depenses", "Plafond de dépenses"),
]

CHAMPS_CANDIDAT = [
    ("civilite", "Civilité"),
    ("nom", "Nom"),
    ("prenom", "Prénom"),
    ("date_naissance", "Date de naissance"),
    ("lieu_naissance", "Lieu de naissance"),
    ("adresse_postale", "Adresse postale"),
    ("code_postal", "Code postal"),
    ("ville", "Ville"),
    ("email", "Email"),
    ("tel", "Téléphone"),
]

CHAMPS_MANDATAIRE = [
    ("civilite", "Civilité"),
    ("nom", "Nom"),
    ("prenom", "Prénom"),
    ("adresse_postale", "Adresse postale"),
    ("code_postal", "Code postal"),
    ("ville", "Ville"),
    ("email", "Email"),
    ("tel", "Téléphone"),
    ("prefecture", "Préfecture de déclaration"),
    ("date_declaration_prefecture", "Date de déclaration en préfecture"),
    ("incompatibilites_verifiees", "Incompatibilités vérifiées"),
    ("capacite_civile_ok", "Capacité civile vérifiée"),
]

CHAMPS_EXPERT = [
    ("nom", "Nom de l'expert-comptable"),
    ("cabinet", "Cabinet"),
    ("adresse_postale", "Adresse postale"),
    ("date_designation", "Date de désignation"),
]

CHAMPS_COMPTE = [
    ("banque", "Banque"),
    ("iban", "IBAN"),
    ("date_ouverture", "Date d'ouverture"),
]


def _rempli(valeur) -> bool:
    """Un booléen à False compte comme non rempli : ces cases sont des attestations."""
    if valeur is None:
        return False
    if isinstance(valeur, bool):
        return valeur
    if isinstance(valeur, str):
        return valeur.strip() != ""
    return True


def _evaluer_objet(obj, champs: list[tuple[str, str]]) -> tuple[int, list[str]]:
    """Nombre de champs remplis et libellés des manquants."""
    if obj is None:
        return 0, [libelle for _, libelle in champs]
    manquants = [libelle for attr, libelle in champs if not _rempli(getattr(obj, attr, None))]
    return len(champs) - len(manquants), manquants


def _section(cle: str, titre: str, total: int, remplis: int, manquants: list[str],
             note: Optional[str] = None) -> dict:
    return {
        "cle": cle,
        "titre": titre,
        "requis": total,
        "remplis": remplis,
        "manquants": manquants,
        "pct": round(remplis / total * 100) if total else 100,
        "complet": not manquants,
        "note": note,
    }


def _section_liste(colistiers: list[Colistier]) -> dict:
    """La liste des candidats : présence, rangs continus, alternance des sexes.

    L'alternance se lit sur la civilité, seule marque du sexe dans le modèle.
    """
    manquants: list[str] = []
    if not colistiers:
        return _section("liste", "Liste des candidats", 3, 0,
                        ["Aucun candidat saisi", "Rangs de la liste", "Alternance femme / homme"])

    ordres = [c.ordre for c in colistiers]
    if any(o is None for o in ordres):
        manquants.append("Rang manquant sur au moins un candidat")
    else:
        attendus = list(range(1, len(colistiers) + 1))
        if sorted(ordres) != attendus:
            manquants.append("Rangs non continus à partir de 1")

    ordonnes = sorted((c for c in colistiers if c.ordre is not None), key=lambda c: c.ordre)
    civilites = [(c.civilite or "").strip().lower() for c in ordonnes]
    if any(not c for c in civilites):
        manquants.append("Civilité manquante sur au moins un candidat")
    elif any(a == b for a, b in zip(civilites, civilites[1:])):
        manquants.append("Alternance femme / homme rompue")

    return _section("liste", "Liste des candidats", 3, 3 - len(manquants), manquants,
                    note=f"{len(colistiers)} candidats")


def evaluer(campaign_id: str) -> dict:
    """État de complétude du dossier, section par section."""
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        election = s.scalars(select(Election)).first()
        candidat = s.scalars(select(Candidat)).first()
        mandataire = s.scalars(select(Mandataire)).first()
        expert = s.scalars(select(ExpertComptable)).first()
        compte = s.scalars(select(CompteBancaire)).first()
        colistiers = list(s.scalars(select(Colistier)).all())

        sections = [
            _section("election", "Élection", len(CHAMPS_ELECTION),
                     *_evaluer_objet(election, CHAMPS_ELECTION)),
            _section("candidat", "Candidat", len(CHAMPS_CANDIDAT),
                     *_evaluer_objet(candidat, CHAMPS_CANDIDAT)),
            _section("mandataire", "Mandataire financier", len(CHAMPS_MANDATAIRE),
                     *_evaluer_objet(mandataire, CHAMPS_MANDATAIRE)),
        ]

        # L'expert-comptable est obligatoire sauf dispense explicite du compte.
        if expert is not None and expert.dispense:
            sections.append(_section("expert_comptable", "Expert-comptable", 1, 1, [],
                                     note="Compte dispensé d'expert-comptable"))
        else:
            sections.append(_section("expert_comptable", "Expert-comptable", len(CHAMPS_EXPERT),
                                     *_evaluer_objet(expert, CHAMPS_EXPERT),
                                     note=None if expert else "Aucun expert-comptable enregistré"))

        sections.append(_section("compte_bancaire", "Compte bancaire", len(CHAMPS_COMPTE),
                                 *_evaluer_objet(compte, CHAMPS_COMPTE)))
        sections.append(_section_liste(colistiers))

    # Pièces annoncées au bordereau mais absentes du disque : l'enveloppe
    # partirait avec un trou que rien ne signale au dépôt.
    import depot  # import tardif : depot dépend de conformite, pas l'inverse.
    absentes = depot.pieces_sans_fichier(campaign_id)
    sections.append(_section(
        "pieces", "Pièces justificatives", 1, 0 if absentes else 1,
        [f"Fichier introuvable : {f}" for f in absentes],
        note=None if absentes else "Tous les fichiers sont présents",
    ))

    requis = sum(sec["requis"] for sec in sections)
    remplis = sum(sec["remplis"] for sec in sections)
    manquants = [f"{sec['titre']} — {m}" for sec in sections for m in sec["manquants"]]

    return {
        "sections": sections,
        "requis": requis,
        "remplis": remplis,
        "pct": round(remplis / requis * 100) if requis else 100,
        "complet": not manquants,
        "manquants": manquants,
    }
