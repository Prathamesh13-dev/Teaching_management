from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from .. import models, dependencies

router = APIRouter(prefix="/whiteboard", tags=["Digital Whiteboard & Saved Lessons"])

class WhiteboardSaveRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=120)
    subject: str = Field(..., min_length=2, max_length=100)
    board_data: str # JSON string of drawing lines / shapes or canvas state
    preview_image: Optional[str] = None # Data URL PNG thumbnail for visual reference

@router.get("/lessons")
def get_saved_lessons(
    subject: Optional[str] = None,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Students and faculty can access saved digital whiteboard lesson notes."""
    query = db.query(models.WhiteboardLesson)
    if subject:
        query = query.filter(models.WhiteboardLesson.subject.ilike(f"%{subject}%"))

    lessons = query.order_by(models.WhiteboardLesson.id.desc()).all()
    return [
        {
            "id": l.id,
            "title": l.title,
            "subject": l.subject,
            "preview_image": l.preview_image,
            "saved_by_id": l.saved_by_id,
            "author_name": l.creator.username if l.creator else "Instructor",
            "time_created": l.time_created.isoformat() if l.time_created else None
        }
        for l in lessons
    ]

@router.get("/lessons/{lesson_id}")
def get_lesson_detail(
    lesson_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Loads complete stroke/drawing data for a saved whiteboard lesson."""
    lesson = db.query(models.WhiteboardLesson).filter(models.WhiteboardLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Whiteboard lesson not found")

    return {
        "id": lesson.id,
        "title": lesson.title,
        "subject": lesson.subject,
        "board_data": lesson.board_data,
        "preview_image": lesson.preview_image,
        "saved_by_id": lesson.saved_by_id,
        "author_name": lesson.creator.username if lesson.creator else "Instructor",
        "time_created": lesson.time_created.isoformat() if lesson.time_created else None
    }

@router.post("/save")
def save_whiteboard_lesson(
    data: WhiteboardSaveRequest,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers/Admins can save their digital whiteboard canvas as a permanent study reference."""
    new_lesson = models.WhiteboardLesson(
        title=data.title.strip(),
        subject=data.subject.strip(),
        board_data=data.board_data,
        preview_image=data.preview_image,
        saved_by_id=current_user.id
    )
    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)

    return {
        "message": f"Whiteboard lesson '{new_lesson.title}' saved successfully!",
        "lesson_id": new_lesson.id,
        "title": new_lesson.title
    }

@router.delete("/lessons/{lesson_id}")
def delete_whiteboard_lesson(
    lesson_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers/Admins can delete a saved whiteboard lesson."""
    lesson = db.query(models.WhiteboardLesson).filter(models.WhiteboardLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Whiteboard lesson not found")

    if current_user.role != models.UserRole.admin and lesson.saved_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete whiteboard lessons you created.")

    db.delete(lesson)
    db.commit()
    return {"message": "Whiteboard lesson deleted successfully."}
