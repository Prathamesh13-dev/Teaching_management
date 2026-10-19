from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from .. import models, dependencies

router = APIRouter(prefix="/attendance", tags=["People & Attendance"])

# --- PYDANTIC SCHEMAS ---
# These define the exact shape of the JSON data we expect from the frontend
class AttendanceRecord(BaseModel):
    student_id: int
    status: str # Expects "Present" or "Absent"

class AttendanceSubmit(BaseModel):
    records: List[AttendanceRecord]

# --- ENDPOINTS ---
@router.get("/students")
def get_students(
    db: Session = Depends(dependencies.get_db), 
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Fetches all registered students."""
    students = db.query(models.User).filter(models.User.role == models.UserRole.student).all()
    # We only return the ID and Username for security!
    return [{"id": s.id, "username": s.username} for s in students]

@router.post("/")
def submit_attendance(
    data: AttendanceSubmit,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher) # Strict RBAC: Only teachers!
):
    """Saves the daily attendance to the database."""
    for record in data.records:
        new_att = models.Attendance(
            student_id=record.student_id, 
            status=record.status
        )
        db.add(new_att)
    
    db.commit()
    return {"message": "Attendance successfully recorded for today!"}