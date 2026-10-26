from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from .database import SessionLocal
from . import models, auth

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user

def get_current_teacher(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role != models.UserRole.teacher:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Teacher privileges required for this action."
        )
    return current_user

def get_current_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin privileges required for this action."
        )
    return current_user

def get_current_teacher_or_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role not in [models.UserRole.teacher, models.UserRole.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Teacher or Administrator privileges required for this action."
        )
    return current_user