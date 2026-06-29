
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import io
import pdf_utils
from database import init_central_db, get_central_db_connection, get_db_connection, update_db_from_excel, push_db_to_excel_and_cloud, CAMPAIGNS_DIR
from dl_owncloud import download_file_from_owncloud
from models import Recette, Depense, SpendingStats
import comptes
import recus
import conformite
import maincourante
import identite
import depot
from db import provision_campaign_db
from typing import List
import os
import re
import uuid
import shutil
import zipfile
import tempfile
from datetime import datetime, timedelta
from pydantic import BaseModel

# Auth imports

# Auth imports
from auth import verify_password, create_access_token, get_current_user, get_password_hash
from config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    OWNCLOUD_HOSTNAME,
    OWNCLOUD_USERNAME,
    OWNCLOUD_PASSWORD,
    OWNCLOUD_SHARE_URL,
    OWNCLOUD_SHARE_PASSWORD,
    BUDGET_REMOTE_FILENAME,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup : initialiser la base centrale
    init_central_db()
    yield
    # Shutdown : rien à nettoyer pour l'instant


app = FastAPI(title="Gestion Budget Campagne", version="1.0.0", lifespan=lifespan)

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

class CampaignCreate(BaseModel):
    name: str

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

def get_active_campaign(request: Request):
    campaign_id = request.cookies.get("campaign_id")
    if not campaign_id:
        return None
    return campaign_id

@app.post("/login")
def login(credentials: LoginRequest, response: Response):
    with get_central_db_connection() as conn:
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

@app.get("/campaigns")
def list_my_campaigns(current_user: dict = Depends(get_current_user)):
    with get_central_db_connection() as conn:
        if current_user["role"] == "admin":
            campaigns = conn.execute("SELECT id, name FROM campaigns").fetchall()
        else:
            campaigns = conn.execute("""
                SELECT c.id, c.name 
                FROM campaigns c 
                JOIN user_campaigns uc ON c.id = uc.campaign_id 
                WHERE uc.username = ?
            """, [current_user["username"]]).fetchall()
    return [{"id": c[0], "name": c[1]} for c in campaigns]

@app.post("/campaigns")
def create_campaign(campaign: CampaignCreate, current_user: dict = Depends(get_current_user)):
    import re
    # Create a slug from the name
    campaign_id = re.sub(r'[^a-zA-Z0-9]', '', campaign.name.lower()) + "_" + datetime.now().strftime("%H%M%S")
    db_name = f"{campaign_id}.db"
    
    with get_central_db_connection() as conn:
        try:
            conn.execute("INSERT INTO campaigns (id, name, db_path) VALUES (?, ?, ?)", 
                         [campaign_id, campaign.name, db_name])
            conn.execute("INSERT INTO user_campaigns (username, campaign_id) VALUES (?, ?)", 
                         [current_user["username"], campaign_id])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erreur lors de la création de la campagne: {str(e)}")

    # Provisionne la base SQLite ORM de la campagne (tables + version Alembic).
    provision_campaign_db(campaign_id)

    return {"id": campaign_id, "name": campaign.name}

@app.post("/select-campaign/{campaign_id}")
def select_campaign(campaign_id: str, response: Response, current_user: dict = Depends(get_current_user)):
    # Verify user has access to this campaign
    with get_central_db_connection() as conn:
        if current_user["role"] == "admin":
            # Admin can select any campaign that exists
            exists = conn.execute("SELECT 1 FROM campaigns WHERE id = ?", [campaign_id]).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Campagne introuvable")
        else:
            # Normal user must be linked to the campaign
            access = conn.execute("SELECT 1 FROM user_campaigns WHERE username = ? AND campaign_id = ?", [current_user["username"], campaign_id]).fetchone()
            if not access:
                raise HTTPException(status_code=403, detail="Vous n'avez pas accès à cette campagne")
    
    response.set_cookie(
        key="campaign_id",
        value=campaign_id,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return {"message": f"Campagne {campaign_id} sélectionnée"}

@app.delete("/campaigns/{campaign_id}")
def delete_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        # Check if the user is at least linked to it? 
        # For safety, let's say only admins can delete the whole campaign file.
        raise HTTPException(status_code=403, detail="Seul un administrateur peut supprimer une campagne")
    
    with get_central_db_connection() as conn:
        # Get db path before deleting
        res = conn.execute("SELECT db_path FROM campaigns WHERE id = ?", [campaign_id]).fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="Campagne introuvable")
        
        db_path = os.path.join(CAMPAIGNS_DIR, res[0])
        
        # Delete from central db
        conn.execute("DELETE FROM user_campaigns WHERE campaign_id = ?", [campaign_id])
        conn.execute("DELETE FROM campaigns WHERE id = ?", [campaign_id])
        
    # Delete the duckdb file if it exists
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception as e:
            # log or ignore if file is locked
            print(f"Could not delete db file {db_path}: {e}")
            
    return {"message": "Campagne supprimée"}

@app.post("/logout")
def logout(response: Response):
    response.delete_cookie("session_token")
    response.delete_cookie("campaign_id")
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
    with get_central_db_connection() as conn:
        users = conn.execute("SELECT username, full_name, role FROM users ORDER BY username").fetchall()
    return [{"username": u[0], "full_name": u[1], "role": u[2]} for u in users]

@app.post("/users")
def create_user(user: UserCreate, admin: dict = Depends(get_current_admin_user)):
    hashed_pwd = get_password_hash(user.password)
    try:
        with get_central_db_connection() as conn:
            conn.execute("INSERT INTO users (username, full_name, hashed_password, role) VALUES (?, ?, ?, ?)",
                         [user.username, user.full_name, hashed_pwd, user.role])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la création (L'utilisateur existe peut-être déjà)")
    return {"message": "Utilisateur créé"}

@app.put("/users/{username}/role")
def update_user_role(username: str, update: UserRoleUpdate, admin: dict = Depends(get_current_admin_user)):
    if username == "gconstant" and update.role != "admin":
         raise HTTPException(status_code=400, detail="Impossible de rétrograder le compte principal")
         

    with get_central_db_connection() as conn:
        conn.execute("UPDATE users SET role = ? WHERE username = ?", [update.role, username])
    return {"message": "Rôle mis à jour"}

@app.delete("/users/{username}")
def delete_user(username: str, admin: dict = Depends(get_current_admin_user)):
    if username == "gconstant":
         raise HTTPException(status_code=400, detail="Impossible de supprimer le compte principal")
    with get_central_db_connection() as conn:
        conn.execute("DELETE FROM users WHERE username = ?", [username])
    return {"message": "Utilisateur supprimé"}

@app.put("/users/{username}/password")
def admin_reset_password(username: str, update: UserPasswordUpdate, admin: dict = Depends(get_current_admin_user)):
    new_hash = get_password_hash(update.password)
    with get_central_db_connection() as conn:
        conn.execute("UPDATE users SET hashed_password = ? WHERE username = ?", [new_hash, username])
    return {"message": "Mot de passe réinitialisé par l'administrateur"}

@app.put("/users/me/password")
def change_password(update: UserPasswordUpdate, current_user: dict = Depends(get_current_user)):
    new_hash = get_password_hash(update.password)
    with get_central_db_connection() as conn:
        conn.execute("UPDATE users SET hashed_password = ? WHERE username = ?", [new_hash, current_user["username"]])
    return {"message": "Mot de passe modifié avec succès"}


# Plafond, taux de remboursement et limite de don sont désormais centralisés
# dans le service `comptes` (le plafond est propre à chaque Election).


def get_campaign_conn(campaign_id: str = Depends(get_active_campaign)):
    if not campaign_id:
        raise HTTPException(status_code=400, detail="Aucune campagne sélectionnée")
    return campaign_id

@app.get("/stats", response_model=SpendingStats)
def get_stats(campaign_id: str = Depends(get_campaign_conn)):
    return SpendingStats(**comptes.compute_stats(campaign_id))

@app.post("/recettes")
def create_recette(recette: Recette, campaign_id: str = Depends(get_campaign_conn)):
    return comptes.create_recette(campaign_id, recette)


@app.put("/recettes/{recette_id}")
def update_recette(recette_id: int, update: Recette, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return comptes.update_recette(campaign_id, recette_id, update)


@app.get("/recettes")
def list_recettes(campaign_id: str = Depends(get_campaign_conn)):
    return comptes.list_recettes(campaign_id)


@app.post("/depenses")
def create_depense(depense: Depense, campaign_id: str = Depends(get_campaign_conn)):
    return comptes.create_depense(campaign_id, depense)


@app.get("/depenses")
def list_depenses(campaign_id: str = Depends(get_campaign_conn)):
    return comptes.list_depenses(campaign_id)


@app.get("/fournisseurs")
def list_fournisseurs(campaign_id: str = Depends(get_campaign_conn)):
    return comptes.list_fournisseurs(campaign_id)

def safe_upload_name(original_name: str) -> str:
    """Assainit un nom de fichier et le rend unique (anti path-traversal / collision)."""
    base = os.path.basename(original_name or "fichier")
    stem, ext = os.path.splitext(base)
    # On ne garde que des caractères sûrs dans le nom
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem).strip("._") or "fichier"
    ext = re.sub(r"[^A-Za-z0-9.]", "", ext)
    return f"{stem}_{uuid.uuid4().hex[:8]}{ext}"


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if not os.path.exists(UPLOADS_DIR):
        os.makedirs(UPLOADS_DIR)
    filename = safe_upload_name(file.filename)
    file_location = os.path.join(UPLOADS_DIR, filename)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    return {"filename": filename, "path": file_location}

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
def export_data(campaign_id: str = Depends(get_campaign_conn)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"export_{campaign_id}_{timestamp}.zip"
    
    tmpdirname = tempfile.mkdtemp()
    depenses_csv_path = os.path.join(tmpdirname, "depenses.csv")
    recettes_csv_path = os.path.join(tmpdirname, "recettes.csv")
    zip_path = os.path.join(tmpdirname, zip_filename)

    import csv
    depenses, recettes = comptes.export_csv_rows(campaign_id)
    for path, rows in ((depenses_csv_path, depenses), (recettes_csv_path, recettes)):
        with open(path, "w", newline="", encoding="utf-8") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(depenses_csv_path, "depenses.csv")
        zipf.write(recettes_csv_path, "recettes.csv")
    
    return FileResponse(zip_path, filename=zip_filename, media_type='application/zip')


# ... (existing imports)
from ocr_utils import extract_text_from_file, analyze_receipt_text

@app.post("/analyze-document")
async def analyze_document(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
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
async def sync_budget(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    """
    Télécharge Budget 2026.xlsx depuis OwnCloud puis synchronise la base de données.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seul un administrateur peut synchroniser le budget")

    # Désactivé temporairement : cette synchro écrit dans l'ancienne base DuckDB.
    # Depuis le passage à l'ORM SQLite, elle créerait une divergence de données.
    # À reporter sur le nouveau modèle (import Excel → ORM) dans une phase ultérieure.
    raise HTTPException(
        status_code=503,
        detail="Synchronisation Budget en cours de portage vers le nouveau modèle de données (indisponible temporairement).",
    )

    # Configuration du téléchargement (lien de partage public, depuis .env)
    downloaded_url = OWNCLOUD_SHARE_URL
    password = OWNCLOUD_SHARE_PASSWORD
    remote_filename = BUDGET_REMOTE_FILENAME
    local_filename = BUDGET_REMOTE_FILENAME

    if not downloaded_url or not password:
        raise HTTPException(
            status_code=500,
            detail="Configuration OwnCloud manquante : définir OWNCLOUD_SHARE_URL et OWNCLOUD_SHARE_PASSWORD dans le fichier .env",
        )

    # Chemin local racine du projet
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_file_path = os.path.join(root_dir, local_filename)

    try:
        # 1. Télécharger le fichier
        download_file_from_owncloud(downloaded_url, password, remote_filename, local_file_path)
        
        # 2. Mettre à jour la base de données
        result = update_db_from_excel(local_file_path, campaign_id=campaign_id)
        return {"message": f"Cloud ok : {result}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Sync Cloud : {str(e)}")

@app.post("/push-budget")
async def push_budget(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    """
    Exporte la base de données vers test.xlsx et l'envoie sur OwnCloud via login.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seul un administrateur peut exporter le budget")

    # Désactivé temporairement : lit l'ancienne base DuckDB (divergente depuis le
    # passage à l'ORM SQLite). À reporter sur le nouveau modèle ultérieurement.
    raise HTTPException(
        status_code=503,
        detail="Export Budget vers OwnCloud en cours de portage vers le nouveau modèle de données (indisponible temporairement).",
    )

    # Configuration OwnCloud issue du fichier .env
    hostname = OWNCLOUD_HOSTNAME
    username = OWNCLOUD_USERNAME
    password = OWNCLOUD_PASSWORD
    remote_filename = f'test_{campaign_id}.xlsx'
    
    try:
        result = push_db_to_excel_and_cloud(hostname, username, password, remote_filename, campaign_id=campaign_id)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _ascii_filename(value: str) -> str:
    """Nom de fichier ASCII sûr pour l'en-tête Content-Disposition (évite les
    erreurs d'encodage d'en-tête HTTP avec les accents)."""
    import unicodedata
    norm = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9._-]", "_", norm) or "fichier"


@app.get("/attestations/recette/{recette_id}")
def get_recette_pdf(recette_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    data = comptes.get_recette_pdf_data(campaign_id, recette_id)
    data["numero_recu"] = recus.numero_recu_pour_recette(campaign_id, recette_id)
    pdf_bytes = pdf_utils.generate_donation_receipt(data, SIGNATURE_PATH)
    filename = _ascii_filename(f"attestation_{data['nom_donateur'] or 'donateur'}") + ".pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/attestations/depense/{depense_id}")
def get_depense_pdf(depense_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    data = comptes.get_depense_pdf_data(campaign_id, depense_id)
    pdf_bytes = pdf_utils.generate_expense_certification(data, SIGNATURE_PATH)
    filename = _ascii_filename(f"justificatif_{data['libelle'] or 'depense'}") + ".pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/attestations/recette/{recette_id}/sent")
def mark_recette_sent(recette_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return comptes.toggle_recette_sent(campaign_id, recette_id)


# --- Carnets de reçus-dons & reçus numérotés (Bloc C) ---

class CarnetCreate(BaseModel):
    numero_carnet: str
    numero_formule_debut: int
    numero_formule_fin: int
    date_retrait_prefecture: str | None = None


class RecuIssue(BaseModel):
    carnet_id: int | None = None


@app.get("/carnets")
def list_carnets(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return recus.list_carnets(campaign_id)


@app.post("/carnets")
def create_carnet(carnet: CarnetCreate, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return recus.create_carnet(campaign_id, carnet.numero_carnet, carnet.numero_formule_debut,
                               carnet.numero_formule_fin, carnet.date_retrait_prefecture)


@app.get("/recus")
def list_recus(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return recus.list_recus(campaign_id)


@app.post("/recettes/{recette_id}/recu")
def issue_recu(recette_id: int, payload: RecuIssue | None = None,
               current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    carnet_id = payload.carnet_id if payload else None
    return recus.issue_recu(campaign_id, recette_id, carnet_id)


@app.post("/recus/{recu_id}/annuler")
def annuler_recu(recu_id: int, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return recus.annuler_recu(campaign_id, recu_id)


# --- Contrôles de conformité (moteur de règles §5) ---

@app.get("/conformite")
def get_conformite(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return conformite.run_checks(campaign_id)


# --- Main courante (annexe 8) ---

@app.get("/main-courante")
def get_main_courante(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return maincourante.journal(campaign_id)


@app.get("/main-courante/export")
def export_main_courante(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    xlsx = maincourante.export_annexe8_xlsx(campaign_id)
    filename = f"main_courante_annexe8_{campaign_id}.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- Identité administrative (socle §6.1) ---

@app.get("/identite")
def get_identite(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.get_identite(campaign_id)


@app.put("/identite/election")
def put_election(payload: identite.ElectionIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.save_election(campaign_id, payload)


@app.put("/identite/candidat")
def put_candidat(payload: identite.CandidatIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.save_candidat(campaign_id, payload)


@app.put("/identite/mandataire")
def put_mandataire(payload: identite.MandataireIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.save_mandataire(campaign_id, payload)


@app.put("/identite/expert-comptable")
def put_expert(payload: identite.ExpertComptableIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.save_expert(campaign_id, payload)


@app.put("/identite/compte-bancaire")
def put_compte(payload: identite.CompteBancaireIn, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return identite.save_compte(campaign_id, payload)


# --- Constitution et dépôt du dossier (Bloc F) ---

class DocumentUpdate(BaseModel):
    enveloppe: str | None = None
    type: str | None = None


@app.get("/documents")
def list_documents(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return depot.list_documents(campaign_id)


@app.put("/documents/{doc_id}")
def update_document(doc_id: int, payload: DocumentUpdate, current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return depot.set_document(campaign_id, doc_id, payload.enveloppe, payload.type)


@app.get("/depot")
def get_depot(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    return depot.get_depot(campaign_id)


@app.get("/depot/export")
def export_depot(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    pdf = depot.export_bordereau_pdf(campaign_id)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=bordereau_depot_{campaign_id}.pdf"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
