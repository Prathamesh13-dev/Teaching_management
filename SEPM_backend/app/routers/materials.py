from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import shutil
import os
from .. import models, dependencies

router = APIRouter(prefix="/materials", tags=["Class Materials"])

# Create an uploads folder to store the files locally
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------
# NEW: Quick route to let you create a Course (Bucket)
# ---------------------------------------------------------
@router.post("/create_course")
def create_course(
    name: str = Form(...),
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher)
):
    """Creates a new course bucket assigned to the logged-in teacher."""
    new_course = models.Course(name=name, teacher_id=current_user.id)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return {"message": "Course created!", "course_id": new_course.id, "name": new_course.name}

@router.post("/upload")
def upload_material(
    title: str = Form(...),
    subject: str = Form(...),
    is_public: bool = Form(True), # NEW: Catch the visibility status (Defaults to True)
    file: UploadFile = File(...),
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher)
):
    """Uploads a file directly into the Teacher's isolated bucket."""
    
    # Save the file locally
    file_location = f"uploads/{file.filename}" # Assuming 'uploads' is your directory
    with open(file_location, "wb+") as file_object:
        import shutil
        shutil.copyfileobj(file.file, file_object)
        
    # NEW: Save the is_public status to the database!
    new_material = models.ClassMaterial(
        title=title, 
        subject=subject,
        file_url=file_location, 
        is_public=is_public, # Passes the True/False value
        uploaded_by_id=current_user.id 
    )
    db.add(new_material)
    db.commit()
    db.refresh(new_material)
    
    return {"message": f"Successfully uploaded '{title}' to {subject}", "file_url": file_location}
# ---------------------------------------------------------
# UPDATED: Get Materials (Now filters by bucket)
# ---------------------------------------------------------
@router.get("/")
def get_materials(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user) # Get whoever is logged in!
):
    """Fetches materials. Students only see public ones; Teachers see all."""
    
    # If the user is a student, filter out the private files
    if current_user.role == models.UserRole.student:
        materials = db.query(models.ClassMaterial).filter(models.ClassMaterial.is_public == True).all()
    
    # If they are a teacher or admin, give them everything
    else:
        materials = db.query(models.ClassMaterial).all()
        
    return materials