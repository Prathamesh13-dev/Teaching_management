from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .. import models, auth, dependencies

router = APIRouter(tags=["Authentication"])

# 1. Define the Pydantic schema to catch the JSON body
class UserCreate(BaseModel):
    username: str
    password: str
    role: str

@router.post("/register")
def create_user(user: UserCreate, db: Session = Depends(dependencies.get_db)): # 2. Use the schema here
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Hash the password and save the user
    hashed_password = auth.get_password_hash(user.password)
    
    # 3. Access the data using user.username, user.password, etc.
    new_user = models.User(username=user.username, hashed_password=hashed_password, role=user.role)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"User {user.username} created successfully as a {user.role}"}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(dependencies.get_db)):
    # Find the user
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    # Verify user exists and password matches
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create the token
    access_token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    
    return {"access_token": access_token, "token_type": "bearer"}
@router.get("/users")
def get_all_users(db: Session = Depends(dependencies.get_db)):
    users = db.query(models.User).all()
    return [{"id": u.id, "username": u.username, "role": u.role} for u in users]

@router.get("/me")
def get_current_profile(current_user: models.User = Depends(dependencies.get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "role": current_user.role}
