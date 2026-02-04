from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class Recette(BaseModel):
    date: date
    nom_donateur: str
    adresse: str
    montant: float
    type: str # 'Don', 'Apport', 'Pret'
    recu_genere: bool = False
    date_envoi: Optional[str] = None

class Depense(BaseModel):
    date: date
    libelle: str
    fournisseur: str
    montant_ttc: float
    tva: float
    categorie_cnccfp: str # 'A1', 'A2', 'B1', etc.
    statut: str # 'Engagé', 'Facturé', 'Payé'
    justificatif_path: Optional[str] = None
    is_nature: bool = False

class SpendingStats(BaseModel):
    total_depenses: float
    total_recettes: float
    plafond: float = 154781.0
    consommation_plafond: float
    estimation_remboursement: float

    reste_a_depenser: float
    nombre_donateurs: int

    solde_tresorerie: float # Recettes - Dépenses Payées
    solde_previsionnel: float # Recettes - Dépenses Totales
    consommation_budget_actuel: float # Dépenses Payées / Recettes * 100
    total_depenses_payees: float
    total_nature_hors_tresorerie: float
