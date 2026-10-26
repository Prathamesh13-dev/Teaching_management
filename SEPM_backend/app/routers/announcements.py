from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from .. import models, dependencies

router = APIRouter(prefix="/announcements", tags=["Class Announcements"])

class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    content: str = Field(..., min_length=5)
    priority: Optional[str] = "Normal" # Normal, Important, Urgent

@router.get("/")
def get_announcements(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Fetches all class announcements."""
    announcements = db.query(models.Announcement).order_by(models.Announcement.id.desc()).all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "priority": a.priority or "Normal",
            "posted_by_id": a.posted_by_id,
            "author_name": a.author.username if a.author else "Faculty",
            "author_role": a.author.role.value if a.author else "teacher",
            "time_created": a.time_created.isoformat() if a.time_created else None
        }
        for a in announcements
    ]

@router.post("/")
def create_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers/Admins can post class announcements to all students."""
    new_announcement = models.Announcement(
        title=data.title.strip(),
        content=data.content.strip(),
        priority=data.priority or "Normal",
        posted_by_id=current_user.id
    )
    db.add(new_announcement)
    db.commit()
    db.refresh(new_announcement)

    return {
        "message": "Announcement posted successfully!",
        "id": new_announcement.id,
        "title": new_announcement.title,
        "priority": new_announcement.priority
    }

@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers/Admins can delete an announcement."""
    announcement = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    if current_user.role != models.UserRole.admin and announcement.posted_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own announcements.")

    db.delete(announcement)
    db.commit()
    return {"message": "Announcement deleted successfully."}
