"""Indemnités kilométriques : un trajet saisi devient une dépense et son justificatif.

Le candidat ou un membre de l'équipe prend sa voiture pour la campagne. Ce
n'est pas une facture : la pièce est un « état de frais kilométriques » qui
dit qui, avec quel véhicule, d'où à où, pourquoi, et comment le montant a été
calculé. La CNCCFP rejette un trajet dont l'objet électoral n'apparaît pas :
d'où l'objet obligatoire.

Aucune table dédiée : la dépense reste une dépense ordinaire (rubrique D1,
avancée par la personne, à rembourser par note de frais), et le détail du
trajet vit dans son libellé et dans le PDF généré, qui devient sa pièce.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import secrets
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

import evenements
import pieces
import validation
from config import SIGNATURE_PATH
from database import ROLE_MANDATAIRE, UPLOADS_DIR
from db import enums
from db.models import Depense, Document
from db.session import campaign_session, ensure_campaign_db

logger = logging.getLogger(__name__)

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "indemnite_km.html"

# Barème kilométrique fiscal, tranche « jusqu'à 5 000 km » : d × taux.
# Inchangé depuis le barème 2024. 7 CV couvre « 7 CV et plus ».
# shortcut: seule la première tranche est gérée ; une campagne dépasse rarement
# 5 000 km par véhicule. Au-delà, il faudrait cumuler les km de l'année.
BAREME_KM: dict[int, Decimal] = {
    3: Decimal("0.529"),
    4: Decimal("0.606"),
    5: Decimal("0.636"),
    6: Decimal("0.665"),
    7: Decimal("0.697"),
}
# Véhicule 100 % électrique : montant majoré de 20 %.
MAJORATION_ELECTRIQUE = Decimal("1.20")


class IndemniteKmIn(BaseModel):
    beneficiaire: str
    qualite: Optional[str] = None  # candidat, membre de l'équipe…
    adresse: Optional[str] = None
    vehicule: str  # marque et modèle
    immatriculation: str
    puissance_cv: int = Field(ge=1, le=50)
    electrique: bool = False
    date: date
    depart: str
    arrivee: str
    aller_retour: bool = True
    km_aller: float = Field(gt=0, le=2000)
    objet: str
    evenement_id: Optional[int] = None
    # Carte grise déjà déposée par /upload : jointe en annexe du PDF.
    carte_grise_path: Optional[str] = None
    visa_mandataire: bool = True


def taux_km(puissance_cv: int, electrique: bool = False) -> Decimal:
    """Taux au km du barème, majoration électrique comprise."""
    cv = min(max(puissance_cv, 3), 7)
    taux = BAREME_KM[cv]
    return taux * MAJORATION_ELECTRIQUE if electrique else taux


def calculer(payload: IndemniteKmIn) -> dict:
    """Distance totale, taux et montant arrondi au centime."""
    km_aller = Decimal(str(payload.km_aller))
    km_total = km_aller * (2 if payload.aller_retour else 1)
    taux = taux_km(payload.puissance_cv, payload.electrique)
    montant = (km_total * taux).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"km_aller": km_aller, "km_total": km_total, "taux": taux, "montant": montant}


def bareme() -> list[dict]:
    """Le barème affiché au formulaire, pour l'aperçu du montant."""
    return [{"puissance_cv": cv, "libelle": f"{cv} CV{' et plus' if cv == 7 else ''}",
             "taux": float(t)} for cv, t in BAREME_KM.items()]


def _fr(valeur: Decimal, decimales: int = 2) -> str:
    return f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")


def _libelle(p: IndemniteKmIn, c: dict) -> str:
    trajet = "A/R" if p.aller_retour else "Aller"
    sep = "↔" if p.aller_retour else "→"
    km = (f"{_fr(c['km_aller'], 1)} + {_fr(c['km_aller'], 1)} = {_fr(c['km_total'], 1)} km"
          if p.aller_retour else f"{_fr(c['km_total'], 1)} km")
    elec = ", électrique +20 %" if p.electrique else ""
    return (f"Indemnités kilométriques — {trajet} {p.depart} {sep} {p.arrivee} "
            f"({km} × {_fr(c['taux'], 3)} €/km, {p.vehicule} {p.puissance_cv} CV"
            f"{elec}, barème fiscal)")


def _data_uri(chemin: Path) -> Optional[str]:
    if not chemin.is_file():
        return None
    ext = chemin.suffix.lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}.get(ext)
    if not mime:
        return None
    return f"data:image/{mime};base64,{base64.b64encode(chemin.read_bytes()).decode()}"


def _entete(campaign_id: str) -> dict:
    import identite

    ident = identite.get_identite(campaign_id)
    election = ident.get("election") or {}
    cand = ident.get("candidat") or {}
    mand = ident.get("mandataire") or {}
    nom = lambda d: " ".join(filter(None, [d.get("civilite"), d.get("prenom"), d.get("nom")])).strip()
    return {
        "election": election.get("libelle") or "",
        "liste": election.get("nom_liste") or "",
        "candidat": nom(cand),
        "mandataire": nom(mand),
    }


def rendre_pdf(campaign_id: str, p: IndemniteKmIn, c: dict, num_piece: str) -> bytes:
    """L'état de frais kilométriques, carte grise en annexe si elle est fournie."""
    # macOS : Pango/GLib viennent de Homebrew (voir calendrier.export_pdf).
    os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")
    from jinja2 import Template
    from weasyprint import HTML

    carte = Path(UPLOADS_DIR) / os.path.basename(p.carte_grise_path) if p.carte_grise_path else None
    html = Template(_TEMPLATE_PATH.read_text(encoding="utf-8")).render(
        entete=_entete(campaign_id), p=p, num_piece=num_piece,
        km_aller=_fr(c["km_aller"], 1), km_total=_fr(c["km_total"], 1),
        taux=_fr(c["taux"], 3), montant=_fr(c["montant"]),
        date=p.date.strftime("%d/%m/%Y"),
        signature=_data_uri(Path(SIGNATURE_PATH)) if p.visa_mandataire else None,
        carte_grise=_data_uri(carte) if carte else None,
    )
    pdf = HTML(string=html).write_pdf()
    if carte and carte.suffix.lower() == ".pdf" and carte.is_file():
        pdf = _ajouter_pdf(pdf, carte)
    return pdf


def _ajouter_pdf(pdf: bytes, annexe: Path) -> bytes:
    """Ajoute à la suite une carte grise déposée en PDF."""
    from pypdf import PdfReader, PdfWriter

    sortie = PdfWriter()
    for source in (PdfReader(io.BytesIO(pdf)), PdfReader(str(annexe))):
        for page in source.pages:
            sortie.add_page(page)
    tampon = io.BytesIO()
    sortie.write(tampon)
    return tampon.getvalue()


def creer(campaign_id: str, payload: IndemniteKmIn, auteur: str) -> dict:
    """Crée la dépense D1, génère son justificatif et l'y rattache."""
    ensure_campaign_db(campaign_id)
    for champ in ("beneficiaire", "vehicule", "immatriculation", "depart", "arrivee", "objet"):
        if not (getattr(payload, champ) or "").strip():
            raise HTTPException(status_code=400, detail=f"Champ obligatoire manquant : {champ}.")
    c = calculer(payload)
    beneficiaire = payload.beneficiaire.strip()

    with campaign_session(campaign_id) as s:
        depense = Depense(
            fournisseur=f"{beneficiaire} (véhicule personnel)",
            nature=_libelle(payload, c),
            montant_ttc=float(c["montant"]),
            tva=0.0,
            date_facture=payload.date,
            rubrique_imputation="D1",
            # Avancée par la personne : reste à rembourser jusqu'au rapprochement.
            statut=enums.StatutDepense.facture,
            reglee=False,
            prise_en_charge=enums.PriseEnCharge.mandataire,
            avance_par=beneficiaire,
        )
        validation.estampiller(depense, auteur, ROLE_MANDATAIRE)
        s.add(depense)
        s.flush()
        num_piece = pieces.attribuer(s, depense)
        if payload.evenement_id:
            evenements.appliquer_liaisons(
                s, depense.id, [evenements.LiaisonEvenementIn(evenement_id=payload.evenement_id)])

        immat = "".join(ch for ch in payload.immatriculation.upper() if ch.isalnum())
        fichier = f"justificatif-IK-{immat}_{num_piece}_{secrets.token_hex(4)}.pdf"
        (Path(UPLOADS_DIR) / fichier).write_bytes(rendre_pdf(campaign_id, payload, c, num_piece))

        doc = Document(type=enums.TypeDocument.autre, media_type="pdf",
                       fichier=fichier, enveloppe=enums.Enveloppe.A)
        validation.estampiller(doc, auteur, ROLE_MANDATAIRE)
        s.add(doc)
        s.flush()
        depense.facture_doc_id = doc.id
        logger.info("IK %s créée : %s €, pièce %s", num_piece, c["montant"], fichier)
        return {"id": depense.id, "num_piece": num_piece, "montant": float(c["montant"]),
                "fichier": fichier}
