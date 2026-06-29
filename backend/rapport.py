"""Rapport PDF de fin de campagne (spec §6.11).

Document interne de pilotage et d'archivage (distinct du formulaire officiel
CNCCFP) : synthèse recettes/dépenses, % de plafond, événements, état de la
checklist de conformité et échéances.
"""

from __future__ import annotations

from datetime import datetime

import comptes
import conformite
import echeancier
import evenements
import identite


def _safe(text: str, limit: int = 110) -> str:
    text = str(text if text is not None else "")[:limit]
    return text.encode("latin-1", "replace").decode("latin-1")


def _eur(v) -> str:
    return f"{(v or 0):,.0f} EUR".replace(",", " ")


def generate(campaign_id: str) -> bytes:
    from fpdf import FPDF

    stats = comptes.compute_stats(campaign_id)
    conf = conformite.run_checks(campaign_id)
    evs = evenements.list_evenements(campaign_id)
    echs = echeancier.echeances(campaign_id)
    ident = identite.get_identite(campaign_id)

    pdf = FPDF()
    pdf.add_page()
    printable = pdf.w - pdf.l_margin - pdf.r_margin

    election = ident.get("election") or {}
    titre = election.get("libelle") or "Campagne"

    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 12, _safe("RAPPORT DE FIN DE CAMPAGNE"), ln=True, align="C")
    pdf.set_font("helvetica", size=11)
    pdf.cell(0, 8, _safe(titre), ln=True, align="C")
    pdf.set_font("helvetica", size=9)
    pdf.cell(0, 6, _safe(f"Édité le {datetime.now().strftime('%d/%m/%Y')}"), ln=True, align="C")
    pdf.ln(4)

    def titre_section(t):
        pdf.ln(2)
        pdf.set_font("helvetica", "B", 13)
        pdf.cell(0, 9, _safe(t), ln=True)
        pdf.set_font("helvetica", size=10)

    def ligne(label, valeur):
        pdf.cell(90, 7, _safe(label))
        pdf.cell(0, 7, _safe(valeur), ln=True)

    # Synthèse financière
    titre_section("Synthèse financière")
    ligne("Total des recettes", _eur(stats["total_recettes"]))
    ligne("Total des dépenses", _eur(stats["total_depenses"]))
    ligne("  dont concours en nature", _eur(stats["total_nature_hors_tresorerie"]))
    ligne("Plafond légal", _eur(stats["plafond"]))
    ligne("Consommation du plafond", f"{stats['consommation_plafond']:.1f} %")
    ligne("Marge restante", _eur(stats["reste_a_depenser"]))
    ligne("Solde de trésorerie", _eur(stats["solde_tresorerie"]))
    ligne("Remboursement estimé", _eur(stats["estimation_remboursement"]))
    ligne("Nombre de donateurs", str(stats["nombre_donateurs"]))

    # Conformité
    titre_section("Conformité")
    c = conf["compteurs"]
    statut = "Prêt à déposer" if conf["pret_a_deposer"] else "NON prêt (points bloquants)"
    ligne("Statut", statut)
    ligne("Bloquants / Avertissements / À compléter",
          f"{c['bloquant']} / {c['avertissement']} / {c['info']}")

    # Événements
    titre_section(f"Événements ({len(evs)})")
    if not evs:
        pdf.cell(0, 6, _safe("  (aucun événement)"), ln=True)
    for e in evs:
        pdf.multi_cell(printable, 6, _safe(
            f"  - {e['date_debut'] or '?'} : {e['titre']} ({e['nb_depenses']} dépenses, coût {_eur(e['cout'])})"))

    # Échéances
    titre_section("Échéances légales")
    if not echs:
        pdf.cell(0, 6, _safe("  (renseigner la date du 1er tour dans l'Identité)"), ln=True)
    for ec in echs:
        pdf.multi_cell(printable, 6, _safe(f"  - {ec['date']} : {ec['libelle']}"))

    return bytes(pdf.output())
