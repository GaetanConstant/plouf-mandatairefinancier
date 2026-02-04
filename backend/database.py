import duckdb
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "campagne.db")

def init_db():
    conn = duckdb.connect(DB_PATH)
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_recettes_id START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_depenses_id START 1;
        
        CREATE TABLE IF NOT EXISTS recettes (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_recettes_id'),
            date DATE,
            nom_donateur VARCHAR,
            adresse VARCHAR,
            montant DOUBLE,
            type VARCHAR,
            recu_genere BOOLEAN DEFAULT FALSE,
            date_envoi VARCHAR
        );
        

        CREATE TABLE IF NOT EXISTS depenses (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_depenses_id'),
            date DATE,
            libelle VARCHAR,
            fournisseur VARCHAR,
            montant_ttc DOUBLE,
            tva DOUBLE,
            categorie_cnccfp VARCHAR,
            statut VARCHAR,
            justificatif_path VARCHAR,
            is_nature BOOLEAN DEFAULT FALSE
        );

        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR PRIMARY KEY,
            full_name VARCHAR,
            hashed_password VARCHAR,
            role VARCHAR DEFAULT 'user'
        );
        
        -- Seed default admin if not exists
        INSERT INTO users (username, full_name, hashed_password, role)
        SELECT 'gconstant', 'Gaëtan CONSTANT MAGNARD', '$2b$12$8kzD/lZzrzY5N1SbcHyQC.xW9a1.9aLeazpcR7N5RV/YxbyGJ48tO', 'admin'
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'gconstant');

        -- Seed default user if not exists
        INSERT INTO users (username, full_name, hashed_password, role)
        SELECT 'mgarabedian', 'Mathieu Garabedian', '$2b$12$8kzD/lZzrzY5N1SbcHyQC.xW9a1.9aLeazpcR7N5RV/YxbyGJ48tO', 'user'
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'mgarabedian');
    """)
    
    # Simple migration for existing database
    try:
        conn.execute("ALTER TABLE recettes ADD COLUMN date_envoi VARCHAR")
    except:
        pass
        
    conn.close()

@contextmanager
def get_db_connection():
    conn = duckdb.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def update_db_from_excel(excel_path):
    import pandas as pd
    
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Le fichier {excel_path} est introuvable.")
    
    # On lit l'excel via pandas pour l'injecter dans DuckDB
    try:
        # Lecture des 7 premières colonnes de l'onglet Municipales
        df_excel = pd.read_excel(excel_path, sheet_name="Municipales - Factures")
        df_excel = df_excel.iloc[:, :7]
        df_excel.columns = ['Date', 'Ordre', 'Piece', 'Categorie', 'Debit', 'Credit', 'Status']
    except Exception as e:
        return f"Erreur de lecture Excel : {e}"

    with get_db_connection() as conn:
        # LOGIQUE D'INIT : On repart sur une base propre pour les données
        conn.execute("BEGIN TRANSACTION")
        try:
            # 1. Suppression des anciennes données et structures de données (Dépenses/Recettes)
            # On ne touche pas à la table 'users'
            conn.execute("DROP TABLE IF EXISTS depenses")
            conn.execute("DROP TABLE IF EXISTS recettes")
            conn.execute("DROP SEQUENCE IF EXISTS seq_depenses_id")
            conn.execute("DROP SEQUENCE IF EXISTS seq_recettes_id")

            # 2. Recréation (La vraie logique de l'init)
            conn.execute("CREATE SEQUENCE seq_recettes_id START 1")
            conn.execute("CREATE SEQUENCE seq_depenses_id START 1")
            
            conn.execute("""
                CREATE TABLE recettes (
                    id INTEGER PRIMARY KEY DEFAULT nextval('seq_recettes_id'),
                    date DATE,
                    nom_donateur VARCHAR,
                    adresse VARCHAR,
                    montant DOUBLE,
                    type VARCHAR,
                    recu_genere BOOLEAN DEFAULT FALSE,
                    date_envoi VARCHAR
                )
            """)
            
            conn.execute("""
                CREATE TABLE depenses (
                    id INTEGER PRIMARY KEY DEFAULT nextval('seq_depenses_id'),
                    date DATE,
                    libelle VARCHAR,
                    fournisseur VARCHAR,
                    montant_ttc DOUBLE,
                    tva DOUBLE,
                    categorie_cnccfp VARCHAR,
                    statut VARCHAR,
                    justificatif_path VARCHAR,
                    is_nature BOOLEAN DEFAULT FALSE
                )
            """)

            # 3. Importation des Dépenses (SQL PUR)
            conn.execute("""
                INSERT INTO depenses (date, libelle, fournisseur, montant_ttc, tva, categorie_cnccfp, statut, justificatif_path, is_nature)
                SELECT 
                    CAST(Date AS DATE), 
                    COALESCE(CAST(Piece AS VARCHAR), 'Sans libellé'), 
                    COALESCE(CAST(Ordre AS VARCHAR), 'Inconnu'), 
                    CAST(Debit AS DOUBLE), 
                    0.0, 
                    COALESCE(CAST(Categorie AS VARCHAR), 'Autre'),
                    CASE 
                        WHEN lower(trim(CAST(Status AS VARCHAR))) = 'nature' THEN 'Réalisé (Nature)'
                        WHEN lower(trim(CAST(Status AS VARCHAR))) IN ('ok', 'payé', 'payé lfi', 'payé') THEN 'Payé'
                        WHEN lower(trim(CAST(Status AS VARCHAR))) = 'prev' THEN 'Engagé'
                        ELSE 'Engagé'
                    END,
                    NULL,
                    CASE WHEN lower(trim(CAST(Status AS VARCHAR))) = 'nature' THEN TRUE ELSE FALSE END
                FROM df_excel
                WHERE Date IS NOT NULL AND Debit > 0
            """)
            
            # 4. Importation des Recettes (Crédit)
            conn.execute("""
                INSERT INTO recettes (date, nom_donateur, adresse, montant, type, recu_genere)
                SELECT 
                    CAST(Date AS DATE), 
                    COALESCE(CAST(Ordre AS VARCHAR), 'Inconnu'), 
                    'Import Excel', 
                    CAST(Credit AS DOUBLE), 
                    COALESCE(CAST(Categorie AS VARCHAR), 'Don'),
                    FALSE
                FROM df_excel
                WHERE Date IS NOT NULL AND Credit > 0
            """)
            
            conn.execute("COMMIT")
            
            # Comptage final
            nb_d = conn.execute("SELECT COUNT(*) FROM depenses").fetchone()[0]
            nb_r = conn.execute("SELECT COUNT(*) FROM recettes").fetchone()[0]
            
            return f"Synchronisation réussie : {nb_d} dépenses et {nb_r} recettes importées."
            
        except Exception as e:
            conn.execute("ROLLBACK")
            return f"Erreur SQL lors de l'import : {str(e)}"

def push_db_to_excel_and_cloud(hostname, username, password, remote_filename):
    import pandas as pd
    import owncloud
    import tempfile
    
    with get_db_connection() as conn:
        df_depenses = conn.execute("SELECT * FROM depenses").fetchdf()
        df_recettes = conn.execute("SELECT * FROM recettes").fetchdf()
    
    # Création du fichier Excel temporaire
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        with pd.ExcelWriter(tmp_path, engine='openpyxl') as writer:
            df_depenses.to_excel(writer, sheet_name='Dépenses', index=False)
            df_recettes.to_excel(writer, sheet_name='Recettes', index=False)
        
        # Connexion avec compte (pour avoir les droits d'écriture)
        oc = owncloud.Client(f"https://{hostname}")
        oc.login(username, password)
        oc.put_file(remote_filename, tmp_path)
        
        return f"Succès : Fichier '{remote_filename}' envoyé sur votre OwnCloud."
    except Exception as e:
        return f"Erreur lors de l'envoi : {str(e)}"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
