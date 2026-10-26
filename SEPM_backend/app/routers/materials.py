from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import shutil
import os
import re
from datetime import datetime
from .. import models, dependencies
from ..storage import UPLOAD_DIR, public_upload_path

router = APIRouter(prefix="/materials", tags=["Class Materials & Documents"])

def sanitize_filename(name: str) -> str:
    # Remove potentially dangerous characters and spaces
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', os.path.basename(name))
    return clean_name or "file"

# --- COURSES / SUBJECT BUCKETS ---

@router.post("/create_course")
def create_course(
    name: str = Form(...),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Creates a new course bucket assigned to the logged-in teacher or admin."""
    new_course = models.Course(
        name=name.strip(),
        code=code.strip() if code else None,
        description=description.strip() if description else None,
        teacher_id=current_user.id
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return {
        "message": "Course created successfully!",
        "course_id": new_course.id,
        "name": new_course.name,
        "code": new_course.code
    }

@router.get("/courses")
def get_courses(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Lists all available courses / buckets."""
    courses = db.query(models.Course).order_by(models.Course.name.asc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "description": c.description,
            "teacher_id": c.teacher_id,
            "teacher_name": c.teacher.username if c.teacher else "Unknown"
        }
        for c in courses
    ]

# --- MATERIALS UPLOAD & MANAGEMENT ---

@router.post("/upload")
def upload_material(
    title: str = Form(...),
    subject: str = Form(...),
    is_public: bool = Form(True),
    course_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Uploads a class document/note into the system."""
    clean_filename = sanitize_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stored_filename = f"{timestamp}_{clean_filename}"
    file_location = UPLOAD_DIR / stored_filename
    
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    ext = os.path.splitext(clean_filename)[1].lower().replace('.', '')
    file_type = "pdf" if ext == "pdf" else ("image" if ext in ["png", "jpg", "jpeg", "gif", "webp"] else "document")

    new_material = models.ClassMaterial(
        title=title.strip(), 
        subject=subject.strip(),
        file_url=public_upload_path(file_location),
        file_type=file_type,
        is_public=is_public,
        course_id=course_id,
        uploaded_by_id=current_user.id 
    )
    db.add(new_material)
    db.commit()
    db.refresh(new_material)
    
    return {
        "message": f"Successfully uploaded '{new_material.title}' to {new_material.subject}",
        "id": new_material.id,
        "file_url": new_material.file_url,
        "title": new_material.title,
        "subject": new_material.subject,
        "file_type": new_material.file_type
    }

@router.get("/")
def get_materials(
    subject: Optional[str] = None,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Fetches materials. Students only see public ones; Teachers & Admins see all."""
    query = db.query(models.ClassMaterial)
    
    if current_user.role == models.UserRole.student:
        query = query.filter(models.ClassMaterial.is_public == True)
        
    if subject:
        query = query.filter(models.ClassMaterial.subject.ilike(f"%{subject}%"))
        
    materials = query.order_by(models.ClassMaterial.id.desc()).all()
    
    results = []
    for m in materials:
        results.append({
            "id": m.id,
            "title": m.title,
            "subject": m.subject,
            "file_url": m.file_url,
            "file_type": m.file_type or "document",
            "is_public": m.is_public,
            "course_id": m.course_id,
            "uploaded_by_id": m.uploaded_by_id,
            "uploader_name": m.uploader.username if m.uploader else "Faculty",
            "time_created": m.time_created.isoformat() if m.time_created else None
        })
    return results

@router.delete("/{material_id}")
def delete_material(
    material_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Deletes a material (Teachers can delete their own; Admins can delete any)."""
    material = db.query(models.ClassMaterial).filter(models.ClassMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
        
    if current_user.role != models.UserRole.admin and material.uploaded_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete materials that you uploaded.")
        
    # Delete local file if exists
    stored_filename = os.path.basename(material.file_url)
    file_location = UPLOAD_DIR / stored_filename
    if file_location.exists():
        try:
            file_location.unlink()
        except Exception:
            pass

    db.delete(material)
    db.commit()
    return {"message": "Material deleted successfully."}