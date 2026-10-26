import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt
import os

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "local-development-secret-change-before-deployment")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours for smooth demos

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compares a plain text password against the hashed version."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Generates a secure hash from a plain text password."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Creates a JWT containing user claims (sub, role, etc.)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)