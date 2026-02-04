
import os
from dotenv import load_dotenv

# Load variables from .env if it exists
load_dotenv()

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week session

# OwnCloud Configuration
OWNCLOUD_HOSTNAME = os.getenv("OWNCLOUD_HOSTNAME", "test.fr")
OWNCLOUD_USERNAME = os.getenv("OWNCLOUD_USERNAME", "toto@gmail.com")
OWNCLOUD_PASSWORD = os.getenv("OWNCLOUD_PASSWORD", "DDDD")
