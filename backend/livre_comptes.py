"""Livre de comptes — export structuré pour l'expert-comptable (spec §6.12).

Génère un classeur Excel multi-onglets :
  - Journal des dépenses (comptes 6xxx)
  - Journal des recettes (comptes 7xxx)
  - Grand livre par rubrique (sous-totaux)
  - État de rapprochement bancaire
  - Index des pièces justificatives

N'inclut que les flux passés par le compte du mandataire (colonnes RA/DA).
"""

from __future__ import annotations

import io

import annexes
import comptes
import depot


def _autosize(ws) -> None:
    for col in ws.columns:
        width = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(width + 2, 60)


def generate_xlsx(campaign_id: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    bold = Font(bold=True)
    recettes = comptes.list_recettes(campaign_id)
    depenses = comptes.list_depenses(campaign_id)
    documents = depot.list_documents(campaign_id)

    wb = Workbook()

    # 1. Journal des dépenses
    ws = wb.active
    ws.title = "Journal dépenses"
    ws.append(["N° pièce", "Date", "Fournisseur", "Nature", "Rubrique (6xxx)",
               "Montant TTC", "Mode", "N° relevé", "Justificatif"])
    for d in depenses:
        ws.append([d.get("num_piece"), d["date"], d["fournisseur"], d["libelle"],
                   d["categorie_cnccfp"], d["montant_ttc"], None, None, d.get("justificatif_path")])

    # 2. Journal des recettes
    wr = wb.create_sheet("Journal recettes")
    wr.append(["N° pièce", "Date", "Donateur / origine", "Nature", "Rubrique (7xxx)",
               "Montant", "Mode", "N° relevé"])
    for r in recettes:
        wr.append([None, r["date"], r["nom_donateur"], r["type"], None, r["montant"], None, None])

    # 3. Grand livre par rubrique
    wg = wb.create_sheet("Grand livre")
    wg.append(["Rubrique", "Sens", "Nombre", "Total (€)"])
    par_rubrique: dict[tuple, list] = {}
    for d in depenses:
        key = (d["categorie_cnccfp"] or "—", "Dépense")
        par_rubrique.setdefault(key, []).append(d["montant_ttc"] or 0.0)
    for r in recettes:
        key = (r["type"] or "—", "Recette")
        par_rubrique.setdefault(key, []).append(r["montant"] or 0.0)
    for (rub, sens), montants in sorted(par_rubrique.items()):
        wg.append([rub, sens, len(montants), round(sum(montants), 2)])

    # 4. État de rapprochement bancaire
    stats = comptes.compute_stats(campaign_id)
    wb_rap = wb.create_sheet("Rapprochement")
    wb_rap.append(["Élément", "Montant (€)"])
    wb_rap.append(["Total recettes encaissées", round(stats["total_recettes"], 2)])
    wb_rap.append(["Total dépenses payées", round(stats["total_depenses_payees"], 2)])
    wb_rap.append(["Solde comptable (recettes - dépenses payées)", round(stats["solde_tresorerie"], 2)])
    wb_rap.append(["Concours en nature (hors compte)", round(stats["total_nature_hors_tresorerie"], 2)])

    # 5. Index des pièces justificatives
    wi = wb.create_sheet("Index pièces")
    wi.append(["N°", "Type", "Fichier", "Enveloppe"])
    for i, doc in enumerate(documents, 1):
        wi.append([i, doc["type_label"], doc["fichier"], doc["enveloppe"]])

    # 6. Emprunts (annexes 3.2 / 3.3 / 3.4)
    we = wb.create_sheet("Emprunts")
    we.append(["Type", "Prêteur", "Pays", "Date contrat", "Durée (mois)", "Date fin", "Taux (%)", "Montant (€)"])
    for e in annexes.list_emprunts(campaign_id):
        preteur = " ".join(filter(None, [e["preteur_civilite"], e["preteur_prenom"], e["preteur_nom"]]))
        we.append([e["type"], preteur, e["preteur_pays"], e["date_contrat"], e["duree_mois"],
                   e["date_fin"], e["taux"], e["montant"]])

    # 7. Colistiers
    wc = wb.create_sheet("Colistiers")
    wc.append(["Civilité", "Prénom", "Nom", "Mandat parlementaire", "1er tour", "2e tour"])
    for col in annexes.list_colistiers(campaign_id):
        wc.append([col["civilite"], col["prenom"], col["nom"], col["mandat_parlementaire"],
                   "Oui" if col["present_tour1"] else "Non", "Oui" if col["present_tour2"] else "Non"])

    # 8. Équipe de campagne (annexe 7)
    wq = wb.create_sheet("Équipe")
    wq.append(["Prénom", "Nom", "Fonction"])
    for mb in annexes.list_equipe(campaign_id):
        wq.append([mb["prenom"], mb["nom"], mb["fonction"]])

    for sheet in wb.worksheets:
        for cell in sheet[1]:
            cell.font = bold
        _autosize(sheet)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
