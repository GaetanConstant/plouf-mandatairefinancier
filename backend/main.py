
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import io
import logging
import pdf_utils
from database import init_central_db, get_central_db_connection, UPLOADS_DIR
import comptes
import depot
import recus
from db import provision_campaign_db
from db.session import campaign_db_path
from deps import (
    get_active_campaign,
    get_campaign_conn,
    get_role,
    mandataire_requis,
    tout_role,
    role_sur_campagne,
)
from database import ROLE_MANDATAIRE, ROLES
from routers import (
    comptes as comptes_routes,
    recus as recus_routes,
    conformite as conformite_routes,
    maincourante as maincourante_routes,
    identite as identite_routes,
    depot as depot_routes,
    pilotage as pilotage_routes,
    mutualisation as mutualisation_routes,
    annexes as annexes_routes,
    validation as validation_routes,
)
import os
import re
import uuid
import shutil
import zipfile
import tempfile
from datetime import datetime, timedelta
from pydantic import BaseModel

# Auth imports
from auth import verify_password, create_access_token, get_current_user, get_password_hash
from config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    COOKIE_SECURE,
    COOKIE_SAMESITE,
    CORS_ORIGINS,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup : base centrale, puis mise à niveau du schéma de chaque campagne.
    init_central_db()
    with get_central_db_connection() as conn:
        campaign_ids = [row[0] for row in conn.execute("SELECT id FROM campaigns").fetchall()]
    for campaign_id in campaign_ids:
        try:
            provision_campaign_db(campaign_id)
        except Exception:
            logger.exception("Migration de la campagne %s impossible", campaign_id)
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
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration du dossier des justificatifs
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Monter le dossier static pour l'accès direct aux fichiers
app.mount("/docs", StaticFiles(directory=UPLOADS_DIR), name="justificatifs")

# Signature scannée du mandataire : hors git (donnée personnelle), déposée à
# côté des données en production. Surchargeable par SIGNATURE_PATH.
SIGNATURE_PATH = os.getenv("SIGNATURE_PATH") or os.path.join(ROOT_DIR, "signature mandataire.png")

@app.get("/health")
def health():
    """Sonde de disponibilité utilisée par le déploiement et la supervision."""
    return {"status": "ok"}


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
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    # Une nouvelle session repart d'une page blanche : sans cela, le cookie de
    # campagne du précédent utilisateur du navigateur reste actif, et l'on entre
    # dans une campagne qu'on n'a pas choisie — voire à laquelle on n'a pas accès.
    response.delete_cookie("campaign_id")

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
    db_name = f"{campaign_id}.sqlite"
    
    with get_central_db_connection() as conn:
        try:
            conn.execute("INSERT INTO campaigns (id, name, db_path) VALUES (?, ?, ?)", 
                         [campaign_id, campaign.name, db_name])
            conn.execute(
                "INSERT INTO user_campaigns (username, campaign_id, role) VALUES (?, ?, ?)",
                [current_user["username"], campaign_id, ROLE_MANDATAIRE])
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
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
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
        
        db_path = campaign_db_path(campaign_id)

        # Delete from central db
        conn.execute("DELETE FROM user_campaigns WHERE campaign_id = ?", [campaign_id])
        conn.execute("DELETE FROM campaigns WHERE id = ?", [campaign_id])
        
    # Supprime le fichier SQLite de la campagne s'il existe encore.
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError as e:
            logger.warning("Suppression du fichier %s impossible : %s", db_path, e)
            
    return {"message": "Campagne supprimée"}

@app.post("/logout")
def logout(response: Response):
    response.delete_cookie("session_token")
    response.delete_cookie("campaign_id")
    return {"message": "Logged out"}

@app.get("/me")
def read_users_me(current_user: dict = Depends(get_current_user),
                  campaign_id: str = Depends(get_active_campaign)):
    """Identité de l'appelant, et son rôle sur la campagne ouverte.

    `role` reste le rôle plateforme (admin / user) ; `role_campagne` est celui
    qui décide de ce que l'interface propose. L'administrateur est mandataire
    de fait, pour pouvoir reprendre la main sur une campagne.
    """
    role_campagne = None
    if campaign_id:
        role_campagne = (ROLE_MANDATAIRE if current_user["role"] == "admin"
                         else role_sur_campagne(current_user["username"], campaign_id))
    return {
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "role_campagne": role_campagne,
    }


@app.get("/campaigns/{campaign_id}/acces")
def list_acces(campaign_id: str, current_user: dict = Depends(get_current_user),
               _garde: str = Depends(mandataire_requis)):
    """Qui a accès à cette campagne, et à quel titre."""
    with get_central_db_connection() as conn:
        lignes = conn.execute(
            "SELECT uc.username, u.full_name, uc.role FROM user_campaigns uc "
            "LEFT JOIN users u ON u.username = uc.username WHERE uc.campaign_id = ? "
            "ORDER BY uc.role, uc.username",
            [campaign_id],
        ).fetchall()
    return [{"username": l[0], "full_name": l[1], "role": l[2]} for l in lignes]


@app.get("/campaigns/{campaign_id}/acces/candidats")
def list_candidats_acces(campaign_id: str, current_user: dict = Depends(get_current_user),
                         _garde: str = Depends(mandataire_requis)):
    """Comptes existants qui n'ont pas encore accès à cette campagne.

    Route distincte de `/users`, réservée aux administrateurs de la plateforme :
    un mandataire doit pouvoir ouvrir sa campagne sans pour autant obtenir la
    liste des comptes avec leurs rôles plateforme.
    """
    with get_central_db_connection() as conn:
        lignes = conn.execute(
            "SELECT u.username, u.full_name FROM users u "
            "WHERE u.username NOT IN ("
            "    SELECT username FROM user_campaigns WHERE campaign_id = ?"
            ") ORDER BY u.full_name, u.username",
            [campaign_id],
        ).fetchall()
    return [{"username": l[0], "full_name": l[1]} for l in lignes]


class AccesIn(BaseModel):
    username: str
    role: str


@app.post("/campaigns/{campaign_id}/acces")
def donner_acces(campaign_id: str, payload: AccesIn,
                 current_user: dict = Depends(get_current_user),
                 _garde: str = Depends(mandataire_requis)):
    """Ouvre la campagne à un compte existant, avec son rôle."""
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Rôle inconnu : {payload.role}")
    with get_central_db_connection() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE username = ?", [payload.username]).fetchone():
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        conn.execute(
            "INSERT INTO user_campaigns (username, campaign_id, role) VALUES (?, ?, ?) "
            "ON CONFLICT(username, campaign_id) DO UPDATE SET role = excluded.role",
            [payload.username, campaign_id, payload.role],
        )
    return {"message": f"Accès accordé à {payload.username} ({payload.role})."}


@app.delete("/campaigns/{campaign_id}/acces/{username}")
def retirer_acces(campaign_id: str, username: str,
                  current_user: dict = Depends(get_current_user),
                  _garde: str = Depends(mandataire_requis)):
    """Un mandataire ne peut pas se retirer lui-même : la campagne resterait sans pilote."""
    if username == current_user["username"]:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas retirer votre propre accès.")
    with get_central_db_connection() as conn:
        conn.execute("DELETE FROM user_campaigns WHERE username = ? AND campaign_id = ?",
                     [username, campaign_id])
    return {"message": f"Accès de {username} retiré."}


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


def safe_upload_name(original_name: str) -> str:
    """Assainit un nom de fichier et le rend unique (anti path-traversal / collision)."""
    base = os.path.basename(original_name or "fichier")
    stem, ext = os.path.splitext(base)
    # On ne garde que des caractères sûrs dans le nom
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem).strip("._") or "fichier"
    ext = re.sub(r"[^A-Za-z0-9.]", "", ext)
    return f"{stem}_{uuid.uuid4().hex[:8]}{ext}"


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user),
                      _garde: str = Depends(tout_role)):
    if not os.path.exists(UPLOADS_DIR):
        os.makedirs(UPLOADS_DIR)
    filename = safe_upload_name(file.filename)
    file_location = os.path.join(UPLOADS_DIR, filename)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    return {"filename": filename, "path": file_location}

@app.get("/justificatifs")
def list_justificatifs(current_user: dict = Depends(get_current_user),
                       _garde: str = Depends(tout_role)):
    """Fichiers présents dans `uploads`, en signalant ceux rattachés à rien.

    Un fichier orphelin — devis remplacé, pièce chargée puis jamais associée —
    n'apparaît dans aucun dossier de dépôt mais encombre le dossier au moment
    de l'envoi à la CNCCFP. Le rattachement se juge sur **toutes** les
    campagnes : `uploads` leur est commun.
    """
    with get_central_db_connection() as conn:
        campaign_ids = [row[0] for row in conn.execute("SELECT id FROM campaigns").fetchall()]
    rattaches = depot.fichiers_rattaches(campaign_ids)

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
                    "url": f"/docs/{filename}",
                    "rattache": filename in rattaches,
                })
    return sorted(files, key=lambda x: x["mtime"], reverse=True)

@app.delete("/justificatifs/{filename}")
def delete_justificatif(filename: str, current_user: dict = Depends(get_current_user),
                        _garde: str = Depends(mandataire_requis)):
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
async def analyze_document(file: UploadFile = File(...), current_user: dict = Depends(get_current_user),
                           _garde: str = Depends(tout_role)):
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
    """Import du budget OwnCloud — désactivé.

    Cette synchro écrivait dans l'ancienne base DuckDB, abandonnée au profit de
    l'ORM SQLite. À reporter sur le nouveau modèle (import Excel → ORM).
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seul un administrateur peut synchroniser le budget")

    raise HTTPException(
        status_code=503,
        detail="Synchronisation Budget en cours de portage vers le nouveau modèle de données (indisponible temporairement).",
    )


@app.post("/push-budget")
async def push_budget(current_user: dict = Depends(get_current_user), campaign_id: str = Depends(get_campaign_conn)):
    """Export du budget vers OwnCloud — désactivé, même raison que `/sync-budget`."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seul un administrateur peut exporter le budget")

    raise HTTPException(
        status_code=503,
        detail="Export Budget vers OwnCloud en cours de portage vers le nouveau modèle de données (indisponible temporairement).",
    )


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
def mark_recette_sent(recette_id: int, current_user: dict = Depends(get_current_user),
                      campaign_id: str = Depends(get_campaign_conn),
                      _garde: str = Depends(mandataire_requis)):
    return comptes.toggle_recette_sent(campaign_id, recette_id)


# --- Montage des routers par domaine ---
app.include_router(comptes_routes.router)
app.include_router(recus_routes.router)
app.include_router(conformite_routes.router)
app.include_router(maincourante_routes.router)
app.include_router(identite_routes.router)
app.include_router(depot_routes.router)
app.include_router(pilotage_routes.router)
app.include_router(mutualisation_routes.router)
app.include_router(annexes_routes.router)
app.include_router(validation_routes.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
