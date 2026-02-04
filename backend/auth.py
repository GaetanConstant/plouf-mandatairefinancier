
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
import jwt
from fastapi import Request, HTTPException, status

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db_connection

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request):
    """
    Dependency to get the current user from the session cookie, fetching from DB.
    """
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        with get_db_connection() as conn:
            user_row = conn.execute("SELECT username, full_name, hashed_password, role FROM users WHERE username = ?", [username]).fetchone()
            
        if user_row is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Return dict matching what main.py expects
        return {
            "username": user_row[0],
            "full_name": user_row[1],
            "hashed_password": user_row[2],
            "role": user_row[3]
        }

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
