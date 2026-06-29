"""Listes fermées (enums) et catalogues de référence.

Ces valeurs sont contrôlées à la saisie : elles rendent les champs
correspondants obligatoires et cohérents, et évitent un retraitement au moment
de l'export pour l'expert-comptable.
"""

from __future__ import annotations

import enum


class TypeElection(str, enum.Enum):
    municipale = "municipale"
    metropole = "metropole"
    secteur = "secteur"
    legislative = "legislative"
    departementale = "departementale"
    regionale = "regionale"
    europeenne = "europeenne"
    autre = "autre"


class TypeMandataire(str, enum.Enum):
    physique = "physique"  # personne physique
    afe = "afe"  # association de financement électorale


class CategorieRecette(str, enum.Enum):
    don = "don"
    apport_perso = "apport_perso"
    pret = "pret"
    contribution_parti = "contribution_parti"
    produit_divers = "produit_divers"
    collecte = "collecte"


class ModePaiement(str, enum.Enum):
    cheque = "cheque"
    virement = "virement"
    cb = "cb"
    prelevement = "prelevement"
    especes = "especes"
    plateforme = "plateforme"


class StatutDepense(str, enum.Enum):
    engage = "engage"  # devis signé
    facture = "facture"  # facturé, en attente de paiement
    paye = "paye"
    realise_nature = "realise_nature"  # concours en nature (hors trésorerie)


class StatutRecuDon(str, enum.Enum):
    delivre = "delivre"
    annule = "annule"
    non_utilise = "non_utilise"


class OrigineConcours(str, enum.Enum):
    candidat = "candidat"
    parti = "parti"
    tiers_pp = "tiers_pp"  # tiers personne physique


class TypeSupport(str, enum.Enum):
    tract = "tract"
    affiche = "affiche"
    flyer = "flyer"
    location_salle = "location_salle"
    prestation = "prestation"
    impression = "impression"
    communication = "communication"
    deplacement = "deplacement"
    autre = "autre"


class TypeEvenement(str, enum.Enum):
    reunion_publique = "reunion_publique"
    collecte = "collecte"
    tractage = "tractage"
    meeting = "meeting"
    porte_a_porte = "porte_a_porte"
    reception = "reception"
    autre = "autre"


class TypeDocument(str, enum.Enum):
    facture = "facture"
    recu = "recu"
    releve_bancaire = "releve_bancaire"
    recepisse = "recepisse"
    photo = "photo"
    contrat = "contrat"
    statuts = "statuts"
    autre = "autre"


class Enveloppe(str, enum.Enum):
    A = "A"  # formulaire + pièces justificatives des dépenses
    B = "B"  # annexes (insérée dans A)
    hors_depot = "hors_depot"


class PorteurMutualise(str, enum.Enum):
    notre_campagne = "notre_campagne"
    partie_externe = "partie_externe"


class PartieMutualisee(str, enum.Enum):
    notre_campagne = "notre_campagne"
    partie_externe = "partie_externe"


class StatutReglementMutualise(str, enum.Enum):
    du = "du"
    percu = "percu"
    regle = "regle"
    sans_objet = "sans_objet"


# ──────────────────────────────────────────────────────────────────────────
# Catalogues de rubriques d'imputation comptable (pivot du livre de comptes).
#
# ⚠️ À FAIRE VALIDER : codes/plan comptable à confirmer avec l'expert-comptable
# et le formulaire CNCCFP. On conserve d'abord les rubriques A1..I1 déjà
# utilisées par l'app, en attendant le mapping vers les comptes 6xxx/7xxx.
# La rubrique reste une chaîne libre côté base, mais validée contre ces
# catalogues au niveau service/API.
# ──────────────────────────────────────────────────────────────────────────

RUBRIQUES_DEPENSE: list[dict[str, str]] = [
    {"code": "A1", "label": "Imprimés, documents, tracts"},
    {"code": "A2", "label": "Frais de distribution"},
    {"code": "A3", "label": "Affiches et frais d'affichage"},
    {"code": "B1", "label": "Réunions publiques, location de salles"},
    {"code": "B2", "label": "Frais de réception, traiteur"},
    {"code": "C1", "label": "Frais postaux et de télécommunications"},
    {"code": "D1", "label": "Frais de transport et de déplacement"},
    {"code": "E1", "label": "Frais de personnel"},
    {"code": "F1", "label": "Frais de gestion et de fonctionnement"},
    {"code": "G1", "label": "Prestataires de services (conseil, communication)"},
    {"code": "H1", "label": "Frais financiers"},
    {"code": "I1", "label": "Divers"},
]

RUBRIQUES_RECETTE: list[dict[str, str]] = [
    {"code": "7010", "label": "Dons de personnes physiques"},
    {"code": "7020", "label": "Apport personnel du candidat"},
    {"code": "7030", "label": "Prêts (personnes physiques / partis)"},
    {"code": "7040", "label": "Contributions des partis politiques"},
    {"code": "7050", "label": "Recettes accessoires (ventes, collectes, manifestations)"},
]

CODES_RUBRIQUE_DEPENSE = {r["code"] for r in RUBRIQUES_DEPENSE}
CODES_RUBRIQUE_RECETTE = {r["code"] for r in RUBRIQUES_RECETTE}
