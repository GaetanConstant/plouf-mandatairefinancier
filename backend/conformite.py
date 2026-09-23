"""Moteur de règles de conformité (spec §5).

Exécute en continu les contrôles qui préviennent un rejet du compte de campagne.
Retourne une liste d'alertes typées par niveau de gravité :

  - bloquant      : motif de rejet du compte / dépôt impossible en l'état
  - avertissement : à corriger avant le dépôt
  - info          : point de vigilance / donnée à compléter

Certaines règles dépendent de champs pas encore saisis par les formulaires
(mode de versement, nationalité/résidence du donateur) : dans ce cas l'alerte
est de niveau « info » (« à renseigner ») plutôt que bloquante.
"""

from __future__ import annotations

import unicodedata

from sqlalchemy import select

from db.models import (
    Candidat,
    CompteBancaire,
    Depense,
    Donateur,
    Election,
    ExpertComptable,
    Mandataire,
    Recette,
    RecuDon,
)
from db.session import campaign_session, ensure_campaign_db
from db import enums

PLAFOND_DEFAUT = 154781.0
LIMITE_DON_INDIVIDUEL = 4600.0
SEUIL_DON_SCRIPTURAL = 150.0          # au-delà : paiement scriptural obligatoire
SEUIL_PLAFOND_ESPECES = 15000.0       # si plafond ≥ ce seuil, les espèces sont plafonnées
PART_MAX_ESPECES = 0.20               # 20 % du plafond

BLOQUANT = "bloquant"
AVERTISSEMENT = "avertissement"
INFO = "info"


def _norm(s: str | None) -> str:
    s = (s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _est_francais_ou_resident(don: Donateur) -> bool | None:
    """True/False si l'info est renseignée, None si inconnue."""
    nat = _norm(don.nationalite)
    res = _norm(don.pays_residence)
    if not nat and not res:
        return None
    fr_terms = ("fr", "france", "francais", "francaise")
    nat_fr = any(t in nat for t in fr_terms) if nat else False
    res_fr = any(t in res for t in fr_terms) if res else False
    return nat_fr or res_fr


def _alerte(code, niveau, message, entite=None, entite_id=None):
    return {"code": code, "niveau": niveau, "message": message,
            "entite": entite, "entite_id": entite_id}


def run_checks(campaign_id: str) -> dict:
    ensure_campaign_db(campaign_id)
    alertes: list[dict] = []

    with campaign_session(campaign_id) as s:
        election = s.scalars(select(Election)).first()
        plafond = (election.plafond_depenses if election and election.plafond_depenses
                   else PLAFOND_DEFAUT)

        recettes = s.scalars(select(Recette)).all()
        depenses = s.scalars(select(Depense)).all()
        recu_recette_ids = set(s.scalars(
            select(RecuDon.recette_id).where(RecuDon.statut == enums.StatutRecuDon.delivre)
        ).all())

        # ── Recettes / dons ───────────────────────────────────────────────
        total_especes_dons = 0.0
        dons_par_donateur: dict[int, float] = {}
        noms: dict[int, str] = {}

        for r in recettes:
            if r.categorie != enums.CategorieRecette.don:
                continue
            don = r.donateur
            nom = don.nom if don else "Donateur inconnu"
            if don:
                noms[don.id] = nom
                dons_par_donateur[don.id] = dons_par_donateur.get(don.id, 0.0) + r.montant

            # Don d'une personne morale → interdit
            if don and not don.est_personne_physique:
                alertes.append(_alerte("don_personne_morale", BLOQUANT,
                    f"Don d'une personne morale interdit : {nom}.", "recette", r.id))

            # Nationalité / résidence
            if don:
                statut_fr = _est_francais_ou_resident(don)
                if statut_fr is False:
                    alertes.append(_alerte("don_etranger", BLOQUANT,
                        f"Donateur ni français ni résident en France : {nom}.", "recette", r.id))
                elif statut_fr is None:
                    alertes.append(_alerte("don_nationalite_inconnue", INFO,
                        f"Nationalité / résidence à renseigner pour {nom}.", "recette", r.id))

            # > 150 € : paiement scriptural obligatoire
            if r.montant > SEUIL_DON_SCRIPTURAL:
                if r.mode == enums.ModePaiement.especes:
                    alertes.append(_alerte("don_especes_sup_150", BLOQUANT,
                        f"Don > 150 € payé en espèces (interdit) : {nom}, {r.montant:.0f} €.", "recette", r.id))
                elif r.mode is None:
                    alertes.append(_alerte("don_mode_inconnu", INFO,
                        f"Mode de versement à préciser pour le don de {nom} ({r.montant:.0f} € > 150 € → scriptural).",
                        "recette", r.id))

            if r.mode == enums.ModePaiement.especes:
                total_especes_dons += r.montant

            # Reçu-don manquant
            if r.id not in recu_recette_ids:
                alertes.append(_alerte("recu_manquant", AVERTISSEMENT,
                    f"Reçu-don non délivré pour {nom} ({r.montant:.0f} €).", "recette", r.id))

        # Plafond 4 600 € par donateur
        for did, total in dons_par_donateur.items():
            if total > LIMITE_DON_INDIVIDUEL:
                alertes.append(_alerte("plafond_donateur", BLOQUANT,
                    f"{noms.get(did)} dépasse le plafond de 4 600 € (total : {total:.0f} €).",
                    "donateur", did))

        # Espèces ≤ 20 % du plafond (si plafond ≥ 15 000 €)
        if plafond >= SEUIL_PLAFOND_ESPECES and total_especes_dons > PART_MAX_ESPECES * plafond:
            alertes.append(_alerte("especes_globales", BLOQUANT,
                f"Total des dons en espèces ({total_especes_dons:.0f} €) supérieur à 20 % du plafond "
                f"({PART_MAX_ESPECES * plafond:.0f} €).", "global", None))

        # ── Dépenses ──────────────────────────────────────────────────────
        total_depenses = 0.0
        total_depenses_payees = 0.0
        for d in depenses:
            total_depenses += d.montant_ttc or 0.0
            est_nature = d.statut == enums.StatutDepense.realise_nature
            if d.statut == enums.StatutDepense.paye:
                total_depenses_payees += d.montant_ttc or 0.0

            if not est_nature and not d.facture_doc_id:
                alertes.append(_alerte("justificatif_manquant", AVERTISSEMENT,
                    f"Justificatif manquant : {d.nature or 'dépense'} ({(d.montant_ttc or 0):.0f} €).",
                    "depense", d.id))
            if d.statut == enums.StatutDepense.paye and not d.num_releve_bancaire:
                alertes.append(_alerte("releve_manquant", AVERTISSEMENT,
                    f"N° de relevé bancaire manquant pour une dépense payée : {d.nature or 'dépense'}.",
                    "depense", d.id))
            if not est_nature and not d.reglee:
                alertes.append(_alerte("depense_non_reglee", INFO,
                    f"Dépense non réglée (à régler avant le dépôt) : {d.nature or 'dépense'}.",
                    "depense", d.id))

        # ── Plafond global & équilibre ────────────────────────────────────
        if total_depenses > plafond:
            alertes.append(_alerte("plafond_depasse", BLOQUANT,
                f"Plafond de dépenses dépassé : {total_depenses:.0f} € > {plafond:.0f} €.", "global", None))

        total_recettes = sum(r.montant for r in recettes)
        solde = total_recettes - total_depenses_payees
        if solde < 0:
            alertes.append(_alerte("compte_decouvert", AVERTISSEMENT,
                f"Trésorerie négative ({solde:.0f} €) : le compte doit être à l'équilibre ou excédentaire.",
                "global", None))

        # ── Identité administrative (formalités substantielles) ───────────
        candidat = s.scalars(select(Candidat)).first()
        mandataire = s.scalars(select(Mandataire)).first()
        expert = s.scalars(select(ExpertComptable)).first()
        compte = s.scalars(select(CompteBancaire)).first()

        if not candidat or not (candidat.nom and candidat.prenom and candidat.adresse_postale
                                and candidat.code_postal and candidat.ville and candidat.email):
            alertes.append(_alerte("candidat_incomplet", AVERTISSEMENT,
                "Identité du candidat incomplète (nom, prénom, adresse, email obligatoires).", "candidat", None))

        if not mandataire:
            alertes.append(_alerte("mandataire_absent", AVERTISSEMENT,
                "Mandataire non renseigné.", "mandataire", None))
        else:
            if mandataire.interdiction_bancaire:
                alertes.append(_alerte("mandataire_interdiction_bancaire", BLOQUANT,
                    "Le mandataire fait l'objet d'une interdiction bancaire.", "mandataire", None))
            if not mandataire.incompatibilites_verifiees:
                alertes.append(_alerte("mandataire_incompatibilites", AVERTISSEMENT,
                    "Incompatibilités du mandataire non vérifiées.", "mandataire", None))
            if not mandataire.date_declaration_prefecture:
                alertes.append(_alerte("mandataire_declaration", AVERTISSEMENT,
                    "Date de déclaration du mandataire en préfecture manquante.", "mandataire", None))

        # Le cas « aucune ligne expert-comptable » échappait au contrôle : la
        # règle ne se déclenchait que si un expert existait déjà, donc un
        # dossier totalement vide sur ce point ne levait aucune alerte.
        if expert is None:
            alertes.append(_alerte("expert_absent", AVERTISSEMENT,
                "Aucun expert-comptable enregistré (obligatoire sauf dispense).",
                "expert_comptable", None))
        elif not expert.dispense and not expert.nom:
            alertes.append(_alerte("expert_incomplet", AVERTISSEMENT,
                "Expert-comptable non renseigné (et compte non dispensé).", "expert_comptable", None))

        if not compte or not compte.date_ouverture:
            alertes.append(_alerte("compte_bancaire_manquant", AVERTISSEMENT,
                "Compte bancaire dédié non renseigné (date d'ouverture manquante).", "compte_bancaire", None))

    compteurs = {
        BLOQUANT: sum(1 for a in alertes if a["niveau"] == BLOQUANT),
        AVERTISSEMENT: sum(1 for a in alertes if a["niveau"] == AVERTISSEMENT),
        INFO: sum(1 for a in alertes if a["niveau"] == INFO),
    }
    # Tri : bloquant d'abord, puis avertissement, puis info.
    ordre = {BLOQUANT: 0, AVERTISSEMENT: 1, INFO: 2}
    alertes.sort(key=lambda a: ordre[a["niveau"]])

    return {
        "alertes": alertes,
        "compteurs": compteurs,
        "pret_a_deposer": compteurs[BLOQUANT] == 0,
    }
