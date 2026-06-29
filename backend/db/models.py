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

class Election(Base):
    __tablename__ = "election"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[enums.TypeElection] = mapped_column(_enum(enums.TypeElection))
    libelle: Mapped[str] = mapped_column(String(255))
    circonscription: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    date_tour1: Mapped[date] = mapped_column(Date)
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
    nationalite: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pays_residence: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    est_personne_physique: Mapped[bool] = mapped_column(Boolean, default=True)

    recettes: Mapped[list["Recette"]] = relationship(back_populates="donateur")


class Recette(Base):
    __tablename__ = "recette"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    compte_id: Mapped[Optional[int]] = mapped_column(ForeignKey("compte_bancaire.id"), nullable=True)
    donateur_id: Mapped[Optional[int]] = mapped_column(ForeignKey("donateur.id"), nullable=True)
    categorie: Mapped[enums.CategorieRecette] = mapped_column(_enum(enums.CategorieRecette))
    montant: Mapped[float] = mapped_column(Float)
    date_versement: Mapped[date] = mapped_column(Date)
    mode: Mapped[enums.ModePaiement] = mapped_column(_enum(enums.ModePaiement))
    num_releve_bancaire: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    num_piece: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rubrique_imputation: Mapped[str] = mapped_column(String(32))  # 7xxx (validée au service)
    justificatif_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document.id"), nullable=True)
    evenement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("evenement.id"), nullable=True)

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

class Depense(Base):
    __tablename__ = "depense"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    compte_id: Mapped[Optional[int]] = mapped_column(ForeignKey("compte_bancaire.id"), nullable=True)
    fournisseur: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # libellé
    montant_ttc: Mapped[float] = mapped_column(Float)
    tva: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    date_reglement: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    mode: Mapped[Optional[enums.ModePaiement]] = mapped_column(_enum(enums.ModePaiement), nullable=True)
    num_releve_bancaire: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
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

class Evenement(Base):
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
# Transverse — Documents & échéances
# ──────────────────────────────────────────────────────────────────────────

class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[enums.TypeDocument] = mapped_column(_enum(enums.TypeDocument))
    media_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # image|pdf|autre
    fichier: Mapped[str] = mapped_column(String(512))  # chemin / nom de fichier
    enveloppe: Mapped[Optional[enums.Enveloppe]] = mapped_column(_enum(enums.Enveloppe), nullable=True)
    date_ajout: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    evenement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("evenement.id"), nullable=True)


class Echeance(Base):
    __tablename__ = "echeance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("election.id"))
    libelle: Mapped[str] = mapped_column(String(255))
    date_cible: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    statut: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    regle_calcul: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
