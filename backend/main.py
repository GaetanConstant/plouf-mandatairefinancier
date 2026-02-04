
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import io
import pdf_utils
from database import init_db, get_db_connection, update_db_from_excel, push_db_to_excel_and_cloud
from dl_owncloud import download_file_from_owncloud
from models import Recette, Depense, SpendingStats
from typing import List
import os
import shutil
import zipfile
import tempfile
from datetime import datetime, timedelta
from pydantic import BaseModel

# Auth imports

# Auth imports
from auth import verify_password, create_access_token, get_current_user, get_password_hash
from config import ACCESS_TOKEN_EXPIRE_MINUTES

app = FastAPI(title="Gestion Budget Campagne", version="1.0.0")

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: str = "user"

class UserRoleUpdate(BaseModel):
    role: str

class UserPasswordUpdate(BaseModel):
    password: str

# CORS middleware to allow requests from frontend
# Note: credentials=True is required for cookies
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Must specify origin for credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration du dossier des justificatifs
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(ROOT_DIR, "data", "uploads")
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

# Monter le dossier static pour l'accès direct aux fichiers
app.mount("/docs", StaticFiles(directory=UPLOADS_DIR), name="justificatifs")

SIGNATURE_PATH = os.path.join(ROOT_DIR, "signature mandataire.png")

# Initialize database on startup
@app.on_event("startup")
def start_db():
    init_db()

@app.post("/login")
def login(credentials: LoginRequest, response: Response):
    with get_db_connection() as conn:
        user = conn.execute("SELECT username, full_name, hashed_password, role FROM users WHERE username = ?", [credentials.username]).fetchone()
    
    if not user or not verify_password(credentials.password, user[2]): # user[2] is hashed_password
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user[0]}, expires_delta=access_token_expires # user[0] is username
    )
    
    # Set HttpOnly cookie
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        samesite="lax", # Important for localhost dev
        secure=False,   # False for localhost, True in prod
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"message": "Login successful", "user": {"username": user[0], "full_name": user[1], "role": user[3]}}

@app.post("/logout")
def logout(response: Response):
    response.delete_cookie("session_token")
    return {"message": "Logged out"}

@app.get("/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    # Return role as well
    return {"username": current_user["username"], "full_name": current_user["full_name"], "role": current_user["role"]}


# --- User Management Endpoints ---

def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Opération réservée aux administrateurs")
    return current_user

@app.get("/users")
def list_users(admin: dict = Depends(get_current_admin_user)):
    with get_db_connection() as conn:
        users = conn.execute("SELECT username, full_name, role FROM users ORDER BY username").fetchall()
    return [{"username": u[0], "full_name": u[1], "role": u[2]} for u in users]

@app.post("/users")
def create_user(user: UserCreate, admin: dict = Depends(get_current_admin_user)):
    hashed_pwd = get_password_hash(user.password)
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO users (username, full_name, hashed_password, role) VALUES (?, ?, ?, ?)",
                         [user.username, user.full_name, hashed_pwd, user.role])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la création (L'utilisateur existe peut-être déjà)")
    return {"message": "Utilisateur créé"}

@app.put("/users/{username}/role")
def update_user_role(username: str, update: UserRoleUpdate, admin: dict = Depends(get_current_admin_user)):
    if username == "gconstant" and update.role != "admin":
         raise HTTPException(status_code=400, detail="Impossible de rétrograder le compte principal")
         

    with get_db_connection() as conn:
        conn.execute("UPDATE users SET role = ? WHERE username = ?", [update.role, username])
    return {"message": "Rôle mis à jour"}

@app.delete("/users/{username}")
def delete_user(username: str, admin: dict = Depends(get_current_admin_user)):
    if username == "gconstant":
         raise HTTPException(status_code=400, detail="Impossible de supprimer le compte principal")
    with get_db_connection() as conn:
        conn.execute("DELETE FROM users WHERE username = ?", [username])
    return {"message": "Utilisateur supprimé"}

@app.put("/users/{username}/password")
def admin_reset_password(username: str, update: UserPasswordUpdate, admin: dict = Depends(get_current_admin_user)):
    new_hash = get_password_hash(update.password)
    with get_db_connection() as conn:
        conn.execute("UPDATE users SET hashed_password = ? WHERE username = ?", [new_hash, username])
    return {"message": "Mot de passe réinitialisé par l'administrateur"}

@app.put("/users/me/password")
def change_password(update: UserPasswordUpdate, current_user: dict = Depends(get_current_user)):
    new_hash = get_password_hash(update.password)
    with get_db_connection() as conn:
        conn.execute("UPDATE users SET hashed_password = ? WHERE username = ?", [new_hash, current_user["username"]])
    return {"message": "Mot de passe modifié avec succès"}

PLAFOND_LEGAL = 154781.0
TAUX_REMBOURSEMENT = 0.475
LIMITE_DON_INDIVIDUEL = 4600.0


@app.get("/stats", response_model=SpendingStats)
def get_stats():
    with get_db_connection() as conn:
        total_depenses = conn.execute("SELECT COALESCE(SUM(montant_ttc), 0) FROM depenses").fetchone()[0]
        # On ne compte que les vrais 'Payé' (non nature) pour la trésorerie
        total_depenses_payees = conn.execute("SELECT COALESCE(SUM(montant_ttc), 0) FROM depenses WHERE statut = 'Payé' AND is_nature = FALSE").fetchone()[0]
        total_nature = conn.execute("SELECT COALESCE(SUM(montant_ttc), 0) FROM depenses WHERE is_nature = TRUE").fetchone()[0]
        total_recettes = conn.execute("SELECT COALESCE(SUM(montant), 0) FROM recettes").fetchone()[0]
        nombre_donateurs = conn.execute("SELECT COUNT(DISTINCT nom_donateur) FROM recettes WHERE type = 'Don'").fetchone()[0]
        
    consommation = (total_depenses / PLAFOND_LEGAL) * 100
    estimation_remboursement = min((total_depenses - total_nature) * TAUX_REMBOURSEMENT, PLAFOND_LEGAL * TAUX_REMBOURSEMENT)
    reste_a_depenser = PLAFOND_LEGAL - total_depenses
    
    # Trésorerie simplifiée
    solde_tresorerie = total_recettes - total_depenses_payees
    solde_previsionnel = total_recettes - (total_depenses - total_nature)
    
    if total_recettes > 0:
        consommation_budget_actuel = (total_depenses_payees / total_recettes) * 100
    else:
        consommation_budget_actuel = 0.0 if total_depenses_payees == 0 else 100.0

    return SpendingStats(
        total_depenses=total_depenses,
        total_depenses_payees=total_depenses_payees,
        total_recettes=total_recettes,
        plafond=PLAFOND_LEGAL,
        consommation_plafond=consommation,
        estimation_remboursement=estimation_remboursement,
        reste_a_depenser=reste_a_depenser,
        nombre_donateurs=nombre_donateurs,
        solde_tresorerie=solde_tresorerie,
        solde_previsionnel=solde_previsionnel,
        consommation_budget_actuel=consommation_budget_actuel,
        total_nature_hors_tresorerie=total_nature
    )

@app.post("/recettes")
def create_recette(recette: Recette):
    # Check limit per donor
    with get_db_connection() as conn:
        current_total = conn.execute("SELECT COALESCE(SUM(montant), 0) FROM recettes WHERE nom_donateur = ? AND type = 'Don'", [recette.nom_donateur]).fetchone()[0]
        if recette.type == 'Don' and (current_total + recette.montant > LIMITE_DON_INDIVIDUEL):
            raise HTTPException(status_code=400, detail=f"Le donateur {recette.nom_donateur} dépasse le plafond de {LIMITE_DON_INDIVIDUEL}€ (Déjà donné: {current_total}€)")

        conn.execute("""
            INSERT INTO recettes (date, nom_donateur, adresse, montant, type, recu_genere, date_envoi)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [recette.date, recette.nom_donateur, recette.adresse, recette.montant, recette.type, recette.recu_genere, recette.date_envoi])
    return {"message": "Recette ajoutée"}


import pandas as pd

# ... (rest of imports)

@app.put("/recettes/{recette_id}")
def update_recette(recette_id: int, update: Recette, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        conn.execute("""
            UPDATE recettes 
            SET nom_donateur = ?, adresse = ?, date = ?, montant = ?, type = ?
            WHERE id = ?
        """, [update.nom_donateur, update.adresse, update.date, update.montant, update.type, recette_id])
    return {"message": "Recette mise à jour"}

@app.get("/recettes")
def list_recettes():
    with get_db_connection() as conn:
        df = conn.execute("SELECT * FROM recettes ORDER BY date DESC").fetchdf()
        # Replace NaN with None for JSON serialization
        df = df.astype(object).where(pd.notnull(df), None)
        return df.to_dict(orient="records")

@app.post("/depenses")
def create_depense(depense: Depense):
    # Force status for nature items if they were set to Payé by mistake in the form
    actual_status = "Réalisé (Nature)" if depense.is_nature else depense.statut
    
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO depenses (date, libelle, fournisseur, montant_ttc, tva, categorie_cnccfp, statut, justificatif_path, is_nature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [depense.date, depense.libelle, depense.fournisseur, depense.montant_ttc, depense.tva, depense.categorie_cnccfp, actual_status, depense.justificatif_path, depense.is_nature])
    return {"message": "Dépense ajoutée"}


@app.get("/depenses")
def list_depenses():
    with get_db_connection() as conn:
        df = conn.execute("SELECT * FROM depenses ORDER BY date DESC").fetchdf()
        df = df.astype(object).where(pd.notnull(df), None)
        return df.to_dict(orient="records")

@app.get("/fournisseurs")
def list_fournisseurs():
    with get_db_connection() as conn:
        # Get unique suppliers, excluding empty ones
        rows = conn.execute("SELECT DISTINCT fournisseur FROM depenses WHERE fournisseur IS NOT NULL AND fournisseur != '' ORDER BY fournisseur ASC").fetchall()
        return [row[0] for row in rows]

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads")
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    file_location = os.path.join(uploads_dir, file.filename)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    return {"filename": file.filename, "path": file_location}

@app.get("/justificatifs")
def list_justificatifs(current_user: dict = Depends(get_current_user)):
    """
    Liste tous les fichiers justificatifs présents sur le serveur.
    """
    files = []
    if os.path.exists(UPLOADS_DIR):
        for filename in os.listdir(UPLOADS_DIR):
            file_path = os.path.join(UPLOADS_DIR, filename)
            if os.path.isfile(file_path):
                stats = os.stat(file_path)
                files.append({
                    "name": filename,
                    "size": stats.st_size,
                    "mtime": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    "url": f"/docs/{filename}"
                })
    return sorted(files, key=lambda x: x["mtime"], reverse=True)

@app.delete("/justificatifs/{filename}")
def delete_justificatif(filename: str, current_user: dict = Depends(get_current_user)):
    """
    Supprime un fichier justificatif.
    """
    file_path = os.path.join(UPLOADS_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": "Fichier supprimé"}
    raise HTTPException(status_code=404, detail="Fichier introuvable")

@app.get("/export")
def export_data():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"export_campagne_{timestamp}.zip"
    
    # We use a temp directory to build the zip
    # Note: In a real app we might clean this up. Auto-cleanup happens on exit of 'with', 
    # but FileResponse needs the file to exist.
    # To properly handle this, we can return the bytes directly or use a background task to delete.
    # For this hackathon scope, we'll write to /tmp and let OS clean up eventually.
    
    tmpdirname = tempfile.mkdtemp()
    depenses_csv_path = os.path.join(tmpdirname, "depenses.csv")
    recettes_csv_path = os.path.join(tmpdirname, "recettes.csv")
    zip_path = os.path.join(tmpdirname, zip_filename)

    with get_db_connection() as conn:
        conn.execute(f"COPY (SELECT * FROM depenses) TO '{depenses_csv_path}' (HEADER, DELIMITER ',')")
        conn.execute(f"COPY (SELECT * FROM recettes) TO '{recettes_csv_path}' (HEADER, DELIMITER ',')")

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(depenses_csv_path, "depenses.csv")
        zipf.write(recettes_csv_path, "recettes.csv")
    
    return FileResponse(zip_path, filename=zip_filename, media_type='application/zip')


# ... (existing imports)
from ocr_utils import extract_text_from_file, analyze_receipt_text

@app.post("/analyze-document")
async def analyze_document(file: UploadFile = File(...)):
    """
    Analyze uploded file (PDF primarily) to extract expense data.
    """
    try:
        content = await file.read()
        text = extract_text_from_file(content, file.filename)
        data = analyze_receipt_text(text)
        
        # Save temp file for preview if needed, or rely on separate upload call later.
        # Actually, let's keep it memory efficient: return data to frontend, frontend will upload file with create_depense.
        return data
    except Exception as e:
        return {"error": str(e), "montant": 0, "date": None, "fournisseur": "", "libelle": ""}

@app.post("/sync-budget")
async def sync_budget(current_user: dict = Depends(get_current_user)):
    """
    Télécharge Budget 2026.xlsx depuis OwnCloud puis synchronise la base de données.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seul un administrateur peut synchroniser le budget")
    
    # Configuration du téléchargement
    downloaded_url = "https://nouveau.cloud117.fr/s/NLEHT4s8rBCZYpQ"
    password = 't88M^v$@scFE' 
    remote_filename = 'Budget 2026.xlsx'
    local_filename = 'Budget 2026.xlsx'
    
    # Chemin local racine du projet
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_file_path = os.path.join(root_dir, local_filename)
    
    try:
        # 1. Télécharger le fichier
        download_file_from_owncloud(downloaded_url, password, remote_filename, local_file_path)
        
        # 2. Mettre à jour la base de données
        result = update_db_from_excel(local_file_path)
        return {"message": f"Cloud ok : {result}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Sync Cloud : {str(e)}")

@app.post("/push-budget")
async def push_budget(current_user: dict = Depends(get_current_user)):
    """
    Exporte la base de données vers test.xlsx et l'envoie sur OwnCloud via login.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seul un administrateur peut exporter le budget")
    
    # Configuration OwnCloud complète
    hostname = 'nouveau.cloud117.fr'
    username = 'gaetanc@pm.me'
    password = 't88M^v$@scFE' 
    remote_filename = 'test.xlsx'
    
    try:
        result = push_db_to_excel_and_cloud(hostname, username, password, remote_filename)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/attestations/recette/{recette_id}")
def get_recette_pdf(recette_id: int, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM recettes WHERE id = ?", [recette_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recette introuvable")
        
        # Mapping row to dict (assuming order from table creation)
        data = {
            "id": row[0],
            "date": row[1].strftime('%d/%m/%Y') if row[1] else 'N/A',
            "nom_donateur": row[2],
            "adresse": row[3],
            "montant": row[4],
            "type": row[5]
        }
        
    pdf_bytes = pdf_utils.generate_donation_receipt(data, SIGNATURE_PATH)
    filename = f"attestation_{data['nom_donateur'].replace(' ', '_')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/attestations/depense/{depense_id}")
def get_depense_pdf(depense_id: int, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM depenses WHERE id = ?", [depense_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dépense introuvable")
        
        data = {
            "id": row[0],
            "date": row[1].strftime('%d/%m/%Y') if row[1] else 'N/A',
            "libelle": row[2],
            "fournisseur": row[3],
            "montant_ttc": row[4],
            "tva": row[5],
            "categorie_cnccfp": row[6]
        }
        
    pdf_bytes = pdf_utils.generate_expense_certification(data, SIGNATURE_PATH)
    filename = f"justificatif_{data['libelle'].replace(' ', '_')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
@app.post("/attestations/recette/{recette_id}/sent")
def mark_recette_sent(recette_id: int, current_user: dict = Depends(get_current_user)):
    with get_db_connection() as conn:
        current = conn.execute("SELECT date_envoi FROM recettes WHERE id = ?", [recette_id]).fetchone()
        if current and current[0]:
            conn.execute("UPDATE recettes SET date_envoi = NULL WHERE id = ?", [recette_id])
            return {"message": "Marquage annulé", "date_envoi": None}
        else:
            today = datetime.now().strftime('%d/%m/%Y %H:%M')
            conn.execute("UPDATE recettes SET date_envoi = ? WHERE id = ?", [today, recette_id])
            return {"message": "Attestation marquée comme envoyée", "date_envoi": today}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
