
# Security Configuration
# In a production environment, SECRET_KEY should be loaded from environment variables.
SECRET_KEY = "super-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week session

# Users Configuration
# Storing hashed password for 'gconstant'
USERS_DB = {
    "gconstant": {
        "username": "gconstant",
        "full_name": "Gaetan Constant",
        "hashed_password": "$2b$12$8kzD/lZzrzY5N1SbcHyQC.xW9a1.9aLeazpcR7N5RV/YxbyGJ48tO"  # bcrypt hash of 'scopa'
    }
}
