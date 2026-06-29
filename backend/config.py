
import os
from dotenv import load_dotenv

# Load variables from .env if it exists
load_dotenv()

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week session

# OwnCloud Configuration
# Identifiants de compte (utilisés pour le push/écriture)
OWNCLOUD_HOSTNAME = os.getenv("OWNCLOUD_HOSTNAME", "")
OWNCLOUD_USERNAME = os.getenv("OWNCLOUD_USERNAME", "")
OWNCLOUD_PASSWORD = os.getenv("OWNCLOUD_PASSWORD", "")

# Lien de partage public (utilisé pour le téléchargement du budget)
OWNCLOUD_SHARE_URL = os.getenv("OWNCLOUD_SHARE_URL", "")
OWNCLOUD_SHARE_PASSWORD = os.getenv("OWNCLOUD_SHARE_PASSWORD", "")
BUDGET_REMOTE_FILENAME = os.getenv("BUDGET_REMOTE_FILENAME", "Budget 2026.xlsx")
