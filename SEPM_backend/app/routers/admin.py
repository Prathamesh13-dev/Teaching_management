from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from .. import models, auth, dependencies

router = APIRouter(prefix="/admin", tags=["Admin Portal & System Governance"])

class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4)
    role: str # student, teacher, admin
    full_name: Optional[str] = None
    email: Optional[str] = None

@router.get("/stats")
def get_system_stats(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Admin dashboard overview: system health, user counts, and platform engagement."""
    total_users = db.query(models.User).count()
    students_count = db.query(models.User).filter(models.User.role == models.UserRole.student).count()
    teachers_count = db.query(models.User).filter(models.User.role == models.UserRole.teacher).count()
    admins_count = db.query(models.User).filter(models.User.role == models.UserRole.admin).count()

    materials_count = db.query(models.ClassMaterial).count()
    assignments_count = db.query(models.Assignment).count()
    submissions_count = db.query(models.Submission).count()
    announcements_count = db.query(models.Announcement).count()
    whiteboard_count = db.query(models.WhiteboardLesson).count()
    groups_count = db.query(models.StudyGroup).count()
    messages_count = db.query(models.Message).count()

    total_attendance = db.query(models.Attendance).count()
    present_attendance = db.query(models.Attendance).filter(models.Attendance.status.ilike("present")).count()
    overall_attendance_pct = round((present_attendance / total_attendance * 100), 1) if total_attendance > 0 else 100.0

    return {
        "users": {
            "total": total_users,
            "students": students_count,
            "teachers": teachers_count,
            "admins": admins_count
        },
        "academics": {
            "materials": materials_count,
            "assignments": assignments_count,
            "submissions": submissions_count,
            "announcements": announcements_count,
            "whiteboards": whiteboard_count
        },
        "collaboration": {
            "groups": groups_count,
            "messages": messages_count
        },
        "attendance": {
            "total_records": total_attendance,
            "overall_rate_pct": overall_attendance_pct
        }
    }

@router.get("/users")
def get_all_users_admin(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Detailed user directory with activity stats for administrative monitoring."""
    users = db.query(models.User).order_by(models.User.id.asc()).all()
    results = []
    for u in users:
        materials_uploaded = len(u.materials) if u.materials else 0
        assignments_done = len(u.submissions) if u.submissions else 0
        attendances_count = len(u.attendances) if u.attendances else 0

        results.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name or u.username,
            "email": u.email or f"{u.username.lower()}@college.edu",
            "role": u.role.value,
            "time_created": u.time_created.isoformat() if u.time_created else None,
            "activity": {
                "materials_uploaded": materials_uploaded,
                "submissions_count": assignments_done,
                "attendance_logs": attendances_count
            }
        })
    return results

@router.post("/users")
def admin_create_user(
    body: AdminUserCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Admin provisioning of new accounts with explicit roles."""
    role_lower = body.role.lower().strip()
    if role_lower not in [models.UserRole.student.value, models.UserRole.teacher.value, models.UserRole.admin.value]:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    existing = db.query(models.User).filter(models.User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username is already taken")

    hashed_pwd = auth.get_password_hash(body.password)
    user = models.User(
        username=body.username.strip(),
        hashed_password=hashed_pwd,
        role=models.UserRole(role_lower),
        full_name=body.full_name or body.username,
        email=body.email or f"{body.username.lower()}@college.edu"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": f"Account '{user.username}' created successfully as {role_lower}",
        "user_id": user.id,
        "username": user.username,
        "role": user.role.value
    }

@router.delete("/content/{content_type}/{content_id}")
def admin_delete_content(
    content_type: str,
    content_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Admin moderation for any content across the platform."""
    type_lower = content_type.lower().strip()
    
    if type_lower == "material":
        item = db.query(models.ClassMaterial).filter(models.ClassMaterial.id == content_id).first()
    elif type_lower == "assignment":
        item = db.query(models.Assignment).filter(models.Assignment.id == content_id).first()
    elif type_lower == "announcement":
        item = db.query(models.Announcement).filter(models.Announcement.id == content_id).first()
    elif type_lower == "whiteboard":
        item = db.query(models.WhiteboardLesson).filter(models.WhiteboardLesson.id == content_id).first()
    elif type_lower == "group":
        item = db.query(models.StudyGroup).filter(models.StudyGroup.id == content_id).first()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {content_type}")

    if not item:
        raise HTTPException(status_code=404, detail=f"{content_type.capitalize()} with ID {content_id} not found")

    db.delete(item)
    db.commit()
    return {"message": f"Successfully removed {content_type} #{content_id} via Admin Moderation."}
