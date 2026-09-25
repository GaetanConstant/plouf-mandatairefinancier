"""Modèle de données métier d'une campagne (un fichier SQLite par campagne).

Organisation par blocs de la spec :
  - Socle        : Election
  - Bloc A/B     : Candidat, Mandataire, AssociationFinancement, ExpertComptable,
                   CompteBancaire, CarnetRecus
  - Bloc C       : Donateur, Recette, RecuDon
  - Bloc D       : Depense, ConcoursNature
  - Événements   : Evenement, EvenementDepense, EvenementConcours
  - Mutualisation: PartieExterne, DepenseMutualisee, RepartitionMutualisee, Convention
  - Transverse   : Document, Echeance

Règle anti-double-comptage : la source de vérité financière est Depense /
ConcoursNature. Le coût par événement se calcule à la volée via `quote_part`
sur les tables de liaison ; il n'est jamais stocké ni réinjecté dans les totaux.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from db import enums


def _enum(py_enum):
    """Stocke l'enum en VARCHAR + CHECK (portable SQLite ↔ Postgres)."""
    return SAEnum(py_enum, native_enum=False, validate_strings=True, length=32)


# ──────────────────────────────────────────────────────────────────────────
# Socle
# ──────────────────────────────────────────────────────────────────────────

class Tracable:
    """Colonnes de traçabilité et de validation.

    Un objet créé par le mandataire naît `valide`. Déposé par l'équipe ou par
    l'expert-comptable, il naît `propose` et reste hors du compte jusqu'à ce
    que le mandataire tranche. Un refus n'efface rien : le motif revient à
    l'auteur, qui peut corriger et resoumettre.
    """

    cree_par: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cree_le: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    statut_validation: Mapped[enums.StatutValidation] = mapped_column(
        _enum(enums.StatutValidation), default=enums.StatutValidation.valide)
    valide_par: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    valide_le: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    motif_refus: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Election(Base):
    __tablename__ = "election"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[enums.TypeElection] = mapped_column(_enum(enums.TypeElection))
    libelle: Mapped[str] = mapped_column(String(255))
    circonscription: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nom_liste: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nuance_politique: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Nullable : une Election peut être créée incomplète (stub de migration /
    # saisie en cours) ; la date est requise au niveau service avant dépôt.
    date_tour1: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_tour2: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Plafond calculé par population, mais stocké (surchargeable).
    plafond_depenses: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Dates calculées par le moteur de dates.
    date_limite_depot: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_cloture_compte: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # La date officielle publiée par l'administration prime sur le calcul.
    date_depot_surcharge: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────────
# Bloc A / B — Identité administrative & compte bancaire
# ──────────────────────────────────────────────────────────────────────────

class AssociationFinancement(Base):
    __tablename__ = "association_financement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    denomination: Mapped[str] = mapped_column(String(255))
    siege_social: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    date_declaration_prefecture: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_publication_jo: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    statuts_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    president_identite: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tresorier_identite: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delib_bureau_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)


class Candidat(Base):
    __tablename__ = "candidat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    civilite: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    nom: Mapped[str] = mapped_column(String(120))
    nom_usage: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    prenom: Mapped[str] = mapped_column(String(120))
    date_naissance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lieu_naissance: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    mandat_parlementaire: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    tete_de_liste: Mapped[bool] = mapped_column(Boolean, default=False)

    adresse_postale: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code_postal: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    ville: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Adresse joignable après le scrutin.
    adresse_post_campagne: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Législatives : identité complète du remplaçant.
    remplacant_identite: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recepisse_candidature_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)


class Mandataire(Base):
    __tablename__ = "mandataire"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    type: Mapped[enums.TypeMandataire] = mapped_column(_enum(enums.TypeMandataire))

    # Si personne physique :
    civilite: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    nom: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    prenom: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    date_naissance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    adresse_postale: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code_postal: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    ville: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Déclaration & conformité :
    date_declaration_prefecture: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    prefecture: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    recepisse_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    accord_expres_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    incompatibilites_verifiees: Mapped[bool] = mapped_column(Boolean, default=False)
    capacite_civile_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    interdiction_bancaire: Mapped[bool] = mapped_column(Boolean, default=False)

    # Si type = afe :
    association_id: Mapped[Optional[int]] = mapped_column(ForeignKey("association_financement.id"), nullable=True)


class ExpertComptable(Base):
    __tablename__ = "expert_comptable"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    dispense: Mapped[bool] = mapped_column(Boolean, default=False)  # compte dispensé d'EC
    cabinet: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nom: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    prenom: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    adresse_postale: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    date_designation: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lettre_mission_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    mission_etendue: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)


class CompteBancaire(Base):
    __tablename__ = "compte_bancaire"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mandataire_id: Mapped[int] = mapped_column(ForeignKey("mandataire.id"))
    banque: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    libelle: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    iban: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    date_ouverture: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_cloture: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    droit_au_compte_active: Mapped[bool] = mapped_column(Boolean, default=False)
    preuves_difficultes_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)


class CarnetRecus(Base):
    __tablename__ = "carnet_recus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    numero_carnet: Mapped[str] = mapped_column(String(64))
    numero_formule_debut: Mapped[int] = mapped_column(Integer)
    numero_formule_fin: Mapped[int] = mapped_column(Integer)
    date_retrait_prefecture: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # nb_utilises / nb_a_restituer : calculés à la volée (non stockés).

    recus: Mapped[list["RecuDon"]] = relationship(back_populates="carnet")


# ──────────────────────────────────────────────────────────────────────────
# Bloc C — Recettes
# ──────────────────────────────────────────────────────────────────────────

class Donateur(Base):
    __tablename__ = "donateur"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(120))
    prenom: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    adresse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # requise pour le reçu fiscal
    code_postal: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    ville: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    nationalite: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pays_residence: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    est_personne_physique: Mapped[bool] = mapped_column(Boolean, default=True)

    recettes: Mapped[list["Recette"]] = relationship(back_populates="donateur")


class Recette(Tracable, Base):
    __tablename__ = "recette"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    compte_id: Mapped[Optional[int]] = mapped_column(ForeignKey("compte_bancaire.id"), nullable=True)
    donateur_id: Mapped[Optional[int]] = mapped_column(ForeignKey("donateur.id"), nullable=True)
    categorie: Mapped[enums.CategorieRecette] = mapped_column(_enum(enums.CategorieRecette))
    montant: Mapped[float] = mapped_column(Float)
    date_versement: Mapped[date] = mapped_column(Date)
    # Nullable : mode inconnu pour les données importées (legacy) ; requis au
    # niveau service pour toute nouvelle saisie.
    mode: Mapped[Optional[enums.ModePaiement]] = mapped_column(_enum(enums.ModePaiement), nullable=True)
    num_releve_bancaire: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    num_cheque_remise: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    date_remise_banque: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    rapprochement: Mapped[bool] = mapped_column(Boolean, default=False)
    num_piece: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rubrique_imputation: Mapped[str] = mapped_column(String(32))  # 7xxx (validée au service)
    justificatif_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    evenement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("evenement.id"), nullable=True)
    emprunt_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # lien Emprunt (applicatif)

    # Suivi de l'envoi de l'attestation au donateur (distinct du statut de la
    # formule dans le carnet, géré par RecuDon en phase 1b).
    recu_genere: Mapped[bool] = mapped_column(Boolean, default=False)
    date_envoi: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    donateur: Mapped[Optional["Donateur"]] = relationship(back_populates="recettes")
    recu: Mapped[Optional["RecuDon"]] = relationship(back_populates="recette", uselist=False)


class RecuDon(Base):
    __tablename__ = "recu_don"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero_formule: Mapped[int] = mapped_column(Integer)
    carnet_id: Mapped[int] = mapped_column(ForeignKey("carnet_recus.id"))
    recette_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recette.id"), nullable=True)
    montant: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    statut: Mapped[enums.StatutRecuDon] = mapped_column(_enum(enums.StatutRecuDon))
    avantage_fiscal_eligible: Mapped[bool] = mapped_column(Boolean, default=False)

    carnet: Mapped["CarnetRecus"] = relationship(back_populates="recus")
    recette: Mapped[Optional["Recette"]] = relationship(back_populates="recu")

    # Numéro de formule unique au sein d'un carnet.
    __table_args__ = (UniqueConstraint("carnet_id", "numero_formule", name="uq_recu_carnet_formule"),)


# ──────────────────────────────────────────────────────────────────────────
# Bloc D — Dépenses & concours en nature
# ──────────────────────────────────────────────────────────────────────────

class Depense(Tracable, Base):
    __tablename__ = "depense"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    compte_id: Mapped[Optional[int]] = mapped_column(ForeignKey("compte_bancaire.id"), nullable=True)
    fournisseur: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # libellé
    montant_ttc: Mapped[float] = mapped_column(Float)
    tva: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    date_facture: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    mode: Mapped[Optional[enums.ModePaiement]] = mapped_column(_enum(enums.ModePaiement), nullable=True)
    num_releve_bancaire: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    num_cheque_remise: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rapprochement: Mapped[bool] = mapped_column(Boolean, default=False)
    num_piece: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rubrique_imputation: Mapped[str] = mapped_column(String(32))  # 6xxx (validée au service)
    facture_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    type_support: Mapped[Optional[enums.TypeSupport]] = mapped_column(_enum(enums.TypeSupport), nullable=True)
    statut: Mapped[enums.StatutDepense] = mapped_column(_enum(enums.StatutDepense), default=enums.StatutDepense.engage)
    reglee: Mapped[bool] = mapped_column(Boolean, default=False)
    cheque_encaisse: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    evenements: Mapped[list["EvenementDepense"]] = relationship(back_populates="depense")


class ConcoursNature(Base):
    __tablename__ = "concours_nature"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    origine: Mapped[enums.OrigineConcours] = mapped_column(_enum(enums.OrigineConcours))
    nature: Mapped[str] = mapped_column(String(255))
    valeur_estimee: Mapped[float] = mapped_column(Float)
    methode_evaluation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rubrique_imputation: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    justificatif_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)

    evenements: Mapped[list["EvenementConcours"]] = relationship(back_populates="concours")


# ──────────────────────────────────────────────────────────────────────────
# Événements + liaisons n-n (avec quote-part)
# ──────────────────────────────────────────────────────────────────────────

class Evenement(Tracable, Base):
    __tablename__ = "evenement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    titre: Mapped[str] = mapped_column(String(255))
    type: Mapped[enums.TypeEvenement] = mapped_column(_enum(enums.TypeEvenement))
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lieu: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    depenses: Mapped[list["EvenementDepense"]] = relationship(back_populates="evenement")
    concours: Mapped[list["EvenementConcours"]] = relationship(back_populates="evenement")


class EvenementDepense(Base):
    __tablename__ = "evenement_depense"

    evenement_id: Mapped[int] = mapped_column(ForeignKey("evenement.id"), primary_key=True)
    depense_id: Mapped[int] = mapped_column(ForeignKey("depense.id"), primary_key=True)
    # % du montant de la dépense affecté à cet événement (Σ d'un objet ≤ 100 %).
    quote_part: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    evenement: Mapped["Evenement"] = relationship(back_populates="depenses")
    depense: Mapped["Depense"] = relationship(back_populates="evenements")


class EvenementConcours(Base):
    __tablename__ = "evenement_concours"

    evenement_id: Mapped[int] = mapped_column(ForeignKey("evenement.id"), primary_key=True)
    concours_id: Mapped[int] = mapped_column(ForeignKey("concours_nature.id"), primary_key=True)
    quote_part: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    evenement: Mapped["Evenement"] = relationship(back_populates="concours")
    concours: Mapped["ConcoursNature"] = relationship(back_populates="evenements")


# ──────────────────────────────────────────────────────────────────────────
# Dépenses mutualisées (conventions avec d'autres candidats)
# ──────────────────────────────────────────────────────────────────────────

class PartieExterne(Base):
    __tablename__ = "partie_externe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(120))
    prenom_ou_liste: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scrutin: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    circonscription: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mandataire_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    adresse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Convention(Base):
    __tablename__ = "convention"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    objet: Mapped[str] = mapped_column(String(255))
    date_signature: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    document_genere_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)

    depenses_mutualisees: Mapped[list["DepenseMutualisee"]] = relationship(back_populates="convention")


class DepenseMutualisee(Base):
    __tablename__ = "depense_mutualisee"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    convention_id: Mapped[Optional[int]] = mapped_column(ForeignKey("convention.id"), nullable=True)
    objet: Mapped[str] = mapped_column(String(255))
    evenement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("evenement.id"), nullable=True)
    montant_total_ttc: Mapped[float] = mapped_column(Float)
    cle_justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    porteur: Mapped[enums.PorteurMutualise] = mapped_column(_enum(enums.PorteurMutualise))
    porteur_partie_id: Mapped[Optional[int]] = mapped_column(ForeignKey("partie_externe.id"), nullable=True)
    # La dépense côté notre compte, si porteur = notre_campagne.
    depense_id: Mapped[Optional[int]] = mapped_column(ForeignKey("depense.id"), nullable=True)

    convention: Mapped[Optional["Convention"]] = relationship(back_populates="depenses_mutualisees")
    repartitions: Mapped[list["RepartitionMutualisee"]] = relationship(back_populates="depense_mutualisee")


class RepartitionMutualisee(Base):
    __tablename__ = "repartition_mutualisee"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    depense_mutualisee_id: Mapped[int] = mapped_column(ForeignKey("depense_mutualisee.id"))
    partie: Mapped[enums.PartieMutualisee] = mapped_column(_enum(enums.PartieMutualisee))
    partie_id: Mapped[Optional[int]] = mapped_column(ForeignKey("partie_externe.id"), nullable=True)
    pourcentage: Mapped[float] = mapped_column(Float)  # Σ par dépense mutualisée = 100 %
    montant: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # calc = total × %
    statut_reglement: Mapped[enums.StatutReglementMutualise] = mapped_column(
        _enum(enums.StatutReglementMutualise), default=enums.StatutReglementMutualise.sans_objet
    )

    depense_mutualisee: Mapped["DepenseMutualisee"] = relationship(back_populates="repartitions")


# ──────────────────────────────────────────────────────────────────────────
# Annexes CNCCFP — colistiers, équipe, emprunts
# ──────────────────────────────────────────────────────────────────────────

class Colistier(Base):
    __tablename__ = "colistier"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    ordre: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    civilite: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    prenom: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    nom: Mapped[str] = mapped_column(String(120))
    mandat_parlementaire: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    present_tour1: Mapped[bool] = mapped_column(Boolean, default=True)
    present_tour2: Mapped[bool] = mapped_column(Boolean, default=False)


class MembreEquipe(Base):
    __tablename__ = "membre_equipe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    prenom: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    nom: Mapped[str] = mapped_column(String(120))
    fonction: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Emprunt(Base):
    __tablename__ = "emprunt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    type: Mapped[enums.TypeEmprunt] = mapped_column(_enum(enums.TypeEmprunt))
    # Prêteur (établissement / parti / personne physique selon le type)
    preteur_nom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    preteur_civilite: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    preteur_prenom: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    preteur_pays: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Contrat
    date_contrat: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    duree_mois: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    date_fin: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    taux: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    montant: Mapped[float] = mapped_column(Float)
    contrat_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)


# ──────────────────────────────────────────────────────────────────────────
# Transverse — Documents & échéances
# ──────────────────────────────────────────────────────────────────────────

class Document(Tracable, Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[enums.TypeDocument] = mapped_column(_enum(enums.TypeDocument))
    media_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # image|pdf|autre
    fichier: Mapped[str] = mapped_column(String(512))  # chemin / nom de fichier
    enveloppe: Mapped[Optional[enums.Enveloppe]] = mapped_column(_enum(enums.Enveloppe), nullable=True)
    date_ajout: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    evenement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("evenement.id"), nullable=True)


class DemandePiece(Base):
    """Réclamation d'un justificatif par l'expert-comptable.

    Rattachée à une dépense quand elle en vise une, libre sinon (« il manque le
    relevé bancaire de septembre »).
    """

    __tablename__ = "demande_piece"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    depense_id: Mapped[Optional[int]] = mapped_column(ForeignKey("depense.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    statut: Mapped[enums.StatutDemandePiece] = mapped_column(
        _enum(enums.StatutDemandePiece), default=enums.StatutDemandePiece.ouverte)
    demande_par: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    demande_le: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reponse: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repondu_par: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    repondu_le: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Releve(Base):
    """Un relevé bancaire importé, quelle qu'en soit la provenance."""

    __tablename__ = "releve"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    compte_id: Mapped[Optional[int]] = mapped_column(ForeignKey("compte_bancaire.id"), nullable=True)
    libelle: Mapped[str] = mapped_column(String(120))  # « Septembre 2026 »
    date_debut: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_fin: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source: Mapped[enums.SourceReleve] = mapped_column(_enum(enums.SourceReleve))
    fichier: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    importe_par: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    importe_le: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    transactions: Mapped[list["TransactionBancaire"]] = relationship(
        back_populates="releve", cascade="all, delete-orphan")


class TransactionBancaire(Base):
    """Une ligne de relevé. Conservée même sans dépense en face : le relevé doit
    rester le reflet fidèle du compte, un écart inexpliqué est précisément ce
    que la commission cherche."""

    __tablename__ = "transaction_bancaire"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    releve_id: Mapped[int] = mapped_column(ForeignKey("releve.id"))
    date_operation: Mapped[date] = mapped_column(Date)
    libelle: Mapped[str] = mapped_column(String(255))
    montant: Mapped[float] = mapped_column(Float)  # toujours positif
    sens: Mapped[enums.SensTransaction] = mapped_column(_enum(enums.SensTransaction))
    reference: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    releve: Mapped["Releve"] = relationship(back_populates="transactions")
    imputations: Mapped[list["ImputationBancaire"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan")


class ImputationBancaire(Base):
    """Part d'une transaction affectée à une dépense.

    Un lien porte un montant : une transaction peut régler plusieurs dépenses,
    et une dépense peut être réglée en plusieurs fois (acompte puis solde).
    """

    __tablename__ = "imputation_bancaire"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transaction_bancaire.id"))
    depense_id: Mapped[int] = mapped_column(ForeignKey("depense.id"))
    montant: Mapped[float] = mapped_column(Float)

    transaction: Mapped["TransactionBancaire"] = relationship(back_populates="imputations")


class Echeance(Base):
    __tablename__ = "echeance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    libelle: Mapped[str] = mapped_column(String(255))
    date_cible: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    statut: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    regle_calcul: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
