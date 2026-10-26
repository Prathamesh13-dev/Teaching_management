from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from .. import models, auth, dependencies

router = APIRouter(tags=["Authentication & Users"])

class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4)
    role: str = "student"
    full_name: Optional[str] = None
    email: Optional[str] = None

class RoleUpdateRequest(BaseModel):
    role: str

@router.post("/register")
def create_user(user: UserCreate, db: Session = Depends(dependencies.get_db)):
    # Public registration may create students only; privileged accounts are provisioned by admins.
    role_lower = user.role.lower().strip()
    if role_lower != models.UserRole.student.value:
        raise HTTPException(status_code=403, detail="Only administrators can create teacher or admin accounts.")

    # Check if username exists
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username is already registered")

    # Hash the password and save the user
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        role=models.UserRole.student,
        full_name=user.full_name or user.username,
        email=user.email or f"{user.username.lower()}@college.edu"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "message": f"User {user.username} created successfully as a {role_lower}",
        "user_id": new_user.id,
        "username": new_user.username,
        "role": new_user.role.value
    }

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(dependencies.get_db)):
    # Find the user by username (case-insensitive search for convenience)
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user:
        # Fallback check case-insensitive
        user = db.query(models.User).filter(models.User.username.ilike(form_data.username)).first()

    # Verify user exists and password matches
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create the token
    access_token = auth.create_access_token(data={"sub": user.username, "role": user.role.value, "user_id": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role.value,
        "user_id": user.id
    }

@router.get("/me")
def get_current_profile(current_user: models.User = Depends(dependencies.get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.value,
        "full_name": current_user.full_name or current_user.username,
        "email": current_user.email
    }

@router.get("/users")
def get_all_users(
    role: Optional[str] = None,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Returns users with optional role filtering."""
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role)
    users = query.order_by(models.User.username.asc()).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role.value,
            "full_name": u.full_name or u.username,
            "email": u.email
        }
        for u in users
    ]

@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    body: RoleUpdateRequest,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Admin-only: updates user role with safeguard against removing the last admin."""
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    new_role = body.role.lower().strip()
    if new_role not in [models.UserRole.student.value, models.UserRole.teacher.value, models.UserRole.admin.value]:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    # Safeguard: Do not allow demoting self if sole admin
    if target_user.id == current_user.id and new_role != models.UserRole.admin.value:
        admin_count = db.query(models.User).filter(models.User.role == models.UserRole.admin).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the only remaining administrator")

    target_user.role = models.UserRole(new_role)
    db.commit()
    db.refresh(target_user)
    return {"message": f"User {target_user.username} role updated to {new_role}", "role": target_user.role.value}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Admin-only: deletes a user with safeguard against deleting oneself."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Administrative safeguard: You cannot delete your own account.")

    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    username = target_user.username
    db.delete(target_user)
    db.commit()
    return {"message": f"User '{username}' was successfully deleted."}
