from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import date as dt_date
from .. import models, dependencies

router = APIRouter(prefix="/attendance", tags=["People & Attendance"])

class AttendanceRecord(BaseModel):
    student_id: int
    status: str # "Present", "Absent", "Late"
    notes: Optional[str] = None

class AttendanceSubmit(BaseModel):
    date: Optional[str] = None # Defaults to YYYY-MM-DD
    records: List[AttendanceRecord]

@router.get("/students")
def get_students(
    db: Session = Depends(dependencies.get_db), 
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Fetches all registered students for attendance or classmate directory."""
    students = db.query(models.User).filter(models.User.role == models.UserRole.student).order_by(models.User.username.asc()).all()
    return [
        {
            "id": s.id,
            "username": s.username,
            "full_name": s.full_name or s.username,
            "email": s.email or f"{s.username.lower()}@college.edu"
        }
        for s in students
    ]

@router.post("/")
def submit_attendance(
    data: AttendanceSubmit,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Records or updates student attendance for a given date."""
    target_date = data.date.strip() if data.date else dt_date.today().isoformat()
    
    saved_count = 0
    for record in data.records:
        # Check if record already exists for this student on this date
        existing = db.query(models.Attendance).filter(
            models.Attendance.student_id == record.student_id,
            models.Attendance.date == target_date
        ).first()

        if existing:
            existing.status = record.status
            existing.notes = record.notes
            existing.marked_by_id = current_user.id
        else:
            new_att = models.Attendance(
                student_id=record.student_id,
                date=target_date,
                status=record.status,
                notes=record.notes,
                marked_by_id=current_user.id
            )
            db.add(new_att)
        saved_count += 1
    
    db.commit()
    return {"message": f"Attendance successfully saved for {target_date} ({saved_count} students recorded).", "date": target_date}

@router.get("/my-summary")
def get_student_attendance(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Students can view their attendance percentage and detailed attendance records."""
    records = db.query(models.Attendance).filter(
        models.Attendance.student_id == current_user.id
    ).order_by(models.Attendance.date.desc()).all()

    total = len(records)
    present_count = sum(1 for r in records if r.status.lower() == "present")
    late_count = sum(1 for r in records if r.status.lower() == "late")
    absent_count = sum(1 for r in records if r.status.lower() == "absent")

    # Present + Late counts toward attended
    percentage = round(((present_count + (0.5 * late_count)) / total) * 100, 1) if total > 0 else 100.0

    history = [
        {
            "id": r.id,
            "date": r.date,
            "status": r.status,
            "notes": r.notes
        }
        for r in records
    ]

    return {
        "student_id": current_user.id,
        "username": current_user.username,
        "total_sessions": total,
        "present_count": present_count,
        "late_count": late_count,
        "absent_count": absent_count,
        "percentage": percentage,
        "history": history
    }

@router.get("/class-summary")
def get_class_attendance_summary(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers/Admins can view class-wide attendance summaries and student percentages."""
    students = db.query(models.User).filter(models.User.role == models.UserRole.student).all()
    all_records = db.query(models.Attendance).all()

    student_stats = []
    for s in students:
        s_records = [r for r in all_records if r.student_id == s.id]
        total = len(s_records)
        present = sum(1 for r in s_records if r.status.lower() == "present")
        late = sum(1 for r in s_records if r.status.lower() == "late")
        absent = sum(1 for r in s_records if r.status.lower() == "absent")
        pct = round(((present + (0.5 * late)) / total) * 100, 1) if total > 0 else 100.0

        student_stats.append({
            "student_id": s.id,
            "username": s.username,
            "full_name": s.full_name or s.username,
            "total_sessions": total,
            "present_count": present,
            "late_count": late,
            "absent_count": absent,
            "percentage": pct
        })

    # Unique dates recorded
    distinct_dates = sorted(list(set(r.date for r in all_records)), reverse=True)

    return {
        "total_students": len(students),
        "total_dates_recorded": len(distinct_dates),
        "dates": distinct_dates,
        "students": student_stats
    }

@router.get("/records")
def get_attendance_records_by_date(
    date: str,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Get attendance records for a specific date."""
    records = db.query(models.Attendance).filter(models.Attendance.date == date).all()
    return [
        {
            "id": r.id,
            "student_id": r.student_id,
            "student_name": r.student.username if r.student else "Student",
            "date": r.date,
            "status": r.status,
            "notes": r.notes
        }
        for r in records
    ]