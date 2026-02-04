
import pandas as pd
import duckdb
import os
from datetime import datetime

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "campagne.db")

# Excel path
EXCEL_PATH = '/Users/gaetanscopa/Documents/mandatairefinancier/Budget 2026.xlsx'
SHEET_NAME = 'Municipales - Factures'

# Category Mapping (same as before for derived simplified code, but now we keep the original as libelle)
CATEGORY_MAP = {
    "Impressions": "A1",
    "Kakemono": "A1",
    "Matériel collage": "A2",
    "Location salle": "B1",
    "Alimentaire évenement": "B2",
    "Captation vidéo meeting": "G1",
    "Photos": "G1",
    "Petit matériel": "I1", 
    "Frais divers": "I1",
    "Divers": "I1"
}

def get_cnccfp_code(text_cat):
    if not isinstance(text_cat, str):
        return "I1"
    text_cat = text_cat.strip()
    return CATEGORY_MAP.get(text_cat, "I1") # Default code if unknown

def clean_statut(status):
    if not isinstance(status, str):
        return "Engagé"
    s = status.lower().strip()
    if s in ['ok', 'payé', 'paye']:
        return "Payé"
    if s in ['prev', 'engagé']:
        return "Engagé"
    return "Facturé"

def run_import():
    print(f"Reading {EXCEL_PATH}...")
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, header=0)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    # Mappings
    # 0 "Date", 1 "Ordre", 2 "Piece", 3 "Categorie", 4 "Debit", 5 "Credit", 6 "Statut"
    
    # NEW MAPPING REQUEST:
    # Ordre (col 1) -> Fournisseur / Donateur
    # Categorie (col 3) -> Libellé
    
    conn = duckdb.connect(DB_PATH)
    

    # Initialize tables if they don't exist
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS id_seq START 1;
        CREATE TABLE IF NOT EXISTS depenses (
            id INTEGER PRIMARY KEY DEFAULT nextval('id_seq'),
            date DATE,
            libelle VARCHAR,
            fournisseur VARCHAR,
            montant_ttc DOUBLE,
            tva DOUBLE,
            categorie_cnccfp VARCHAR,
            statut VARCHAR,
            justificatif_path VARCHAR
        );
        CREATE TABLE IF NOT EXISTS recettes (
            id INTEGER PRIMARY KEY DEFAULT nextval('id_seq'),
            date DATE,
            nom_donateur VARCHAR,
            adresse VARCHAR,
            montant DOUBLE,
            type VARCHAR,
            recu_genere BOOLEAN
        );
    """)

    # Drop existing tables to refresh data structure and content
    conn.execute("DELETE FROM depenses")
    conn.execute("DELETE FROM recettes")
    
    added_recettes = 0
    added_depenses = 0

    print("Starting re-import with new mapping logic...")

    for index, row in df.iterrows():
        try:
            # Column access by index to be safe against header names changes
            date_val = row.iloc[0]
            ordre_val = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else "Inconnu" # Becomes Fournisseur/Donateur
            piece_val = str(row.iloc[2]).strip() if not pd.isna(row.iloc[2]) else None
            categorie_val = str(row.iloc[3]).strip() if not pd.isna(row.iloc[3]) else "Divers" # Becomes Libellé
            debit = float(row.iloc[4]) if not pd.isna(row.iloc[4]) else 0.0
            credit = float(row.iloc[5]) if not pd.isna(row.iloc[5]) else 0.0
            statut_val = clean_statut(str(row.iloc[6])) if not pd.isna(row.iloc[6]) else "Engagé"

            if pd.isna(date_val):
                continue
            
            if isinstance(date_val, datetime):
                date_str = date_val.date()
            else:
                continue

            # --- DEPENSE ---
            if debit > 0:
                # Logic: Categorie -> Libellé
                # Logic: Ordre -> Fournisseur
                # Category Code derived from Categorie
                cnccfp_code = get_cnccfp_code(categorie_val)
                
                conn.execute("""
                    INSERT INTO depenses (date, libelle, fournisseur, montant_ttc, tva, categorie_cnccfp, statut, justificatif_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [date_str, categorie_val, ordre_val, debit, 0.0, cnccfp_code, statut_val, piece_val])
                added_depenses += 1

            # --- RECETTE ---
            if credit > 0:
                recette_type = "Don"
                if "prêt" in categorie_val.lower() or "pret" in categorie_val.lower():
                    recette_type = "Pret"
                elif "apport" in categorie_val.lower():
                    recette_type = "Apport"

                # Logic: Ordre -> Nom Donateur
                # Logic: Categorie -> (Implicitly type indicator but maybe keep?) No field for libelle in Recette except type
                
                conn.execute("""
                    INSERT INTO recettes (date, nom_donateur, adresse, montant, type, recu_genere)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [date_str, ordre_val, "Inconnue", credit, recette_type, False])
                added_recettes += 1

        except Exception as e:
            print(f"Error on row {index}: {e}")

    conn.close()
    print(f"Re-import complete. Added {added_depenses} expenses and {added_recettes} revenues.")

if __name__ == "__main__":
    run_import()
