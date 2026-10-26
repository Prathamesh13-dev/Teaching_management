from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import shutil
import os
import re
from datetime import datetime
from .. import models, dependencies
from ..storage import ASSIGNMENT_UPLOAD_DIR, UPLOAD_DIR, public_upload_path

router = APIRouter(prefix="/assignments", tags=["Assignments & Submissions (Google Classroom)"])

def sanitize_filename(name: str) -> str:
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', os.path.basename(name))
    return clean_name or "submission"

class GradeRequest(BaseModel):
    grade: float
    feedback: Optional[str] = None

@router.get("/")
def get_assignments(
    subject: Optional[str] = None,
    course_id: Optional[int] = None,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Lists all class assignments. Includes submission status for the logged-in student."""
    query = db.query(models.Assignment)
    if course_id:
        query = query.filter(models.Assignment.course_id == course_id)
    elif subject:
        query = query.filter(models.Assignment.subject.ilike(f"%{subject}%"))
        
    assignments = query.order_by(models.Assignment.id.desc()).all()

    # Pre-fetch student's submissions if student
    student_submissions = {}
    if current_user.role == models.UserRole.student:
        subs = db.query(models.Submission).filter(models.Submission.student_id == current_user.id).all()
        student_submissions = {s.assignment_id: s for s in subs}

    results = []
    for a in assignments:
        item = {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "subject": a.subject,
            "course_id": a.course_id,
            "due_date": a.due_date,
            "max_points": a.max_points,
            "attachment_url": a.attachment_url,
            "creator_id": a.created_by_id,
            "creator_name": a.creator.username if a.creator else "Faculty",
            "time_created": a.time_created.isoformat() if a.time_created else None,
            "total_submissions": len(a.submissions)
        }

        if current_user.role == models.UserRole.student:
            sub = student_submissions.get(a.id)
            item["my_submission"] = {
                "id": sub.id,
                "file_url": sub.file_url,
                "status": sub.status,
                "grade": sub.grade,
                "feedback": sub.feedback,
                "student_notes": sub.student_notes,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None
            } if sub else None

        results.append(item)

    return results

@router.post("/")
def create_assignment(
    title: str = Form(...),
    description: str = Form(...),
    subject: str = Form(...),
    due_date: str = Form(...),
    max_points: int = Form(100),
    course_id: Optional[int] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers/Admins can create new coursework assignments with deadlines."""
    attachment_path = None
    if attachment and attachment.filename:
        clean_name = sanitize_filename(attachment.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        attachment_file = UPLOAD_DIR / f"{timestamp}_{clean_name}"
        attachment_path = public_upload_path(attachment_file)
        with open(attachment_file, "wb+") as f:
            shutil.copyfileobj(attachment.file, f)

    new_assignment = models.Assignment(
        title=title.strip(),
        description=description.strip(),
        subject=subject.strip(),
        due_date=due_date.strip(),
        max_points=max_points,
        course_id=course_id,
        attachment_url=attachment_path,
        created_by_id=current_user.id
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)

    return {
        "message": f"Assignment '{new_assignment.title}' created successfully!",
        "assignment_id": new_assignment.id
    }

@router.delete("/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers/Admins can delete an assignment and its submissions."""
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()
    return {"message": f"Assignment '{assignment.title}' deleted successfully."}

@router.post("/{assignment_id}/submit")
def submit_assignment(
    assignment_id: int,
    student_notes: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Students can upload assignment submissions."""
    if current_user.role != models.UserRole.student:
        raise HTTPException(status_code=403, detail="Only students can submit assignments.")

    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Save uploaded file
    clean_name = sanitize_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_location = ASSIGNMENT_UPLOAD_DIR / f"{timestamp}_{current_user.username}_{clean_name}"
    file_path = public_upload_path(file_location)
    
    with open(file_location, "wb+") as f:
        shutil.copyfileobj(file.file, f)

    # Check for existing submission to allow resubmission
    existing_sub = db.query(models.Submission).filter(
        models.Submission.assignment_id == assignment_id,
        models.Submission.student_id == current_user.id
    ).first()

    if existing_sub:
        existing_sub.file_url = file_path
        existing_sub.student_notes = student_notes
        existing_sub.submitted_at = datetime.now()
        existing_sub.status = "Resubmitted"
        db.commit()
        db.refresh(existing_sub)
        return {"message": "Assignment work updated successfully!", "submission_id": existing_sub.id}

    new_sub = models.Submission(
        assignment_id=assignment_id,
        student_id=current_user.id,
        file_url=file_path,
        student_notes=student_notes,
        status="Submitted"
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)

    return {"message": "Assignment successfully submitted!", "submission_id": new_sub.id}

@router.get("/{assignment_id}/submissions")
def get_assignment_submissions(
    assignment_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers/Admins can review all submissions for an assignment."""
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    submissions = db.query(models.Submission).filter(
        models.Submission.assignment_id == assignment_id
    ).order_by(models.Submission.submitted_at.desc()).all()

    return [
        {
            "id": s.id,
            "student_id": s.student_id,
            "student_name": s.student.username if s.student else "Unknown",
            "file_url": s.file_url,
            "student_notes": s.student_notes,
            "grade": s.grade,
            "feedback": s.feedback,
            "status": s.status,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "max_points": assignment.max_points
        }
        for s in submissions
    ]

@router.put("/submissions/{submission_id}/grade")
def grade_submission(
    submission_id: int,
    body: GradeRequest,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers/Admins can grade and provide feedback on student submissions."""
    sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    sub.grade = body.grade
    sub.feedback = body.feedback.strip() if body.feedback else None
    sub.status = "Graded"
    sub.graded_at = datetime.now()

    db.commit()
    db.refresh(sub)

    return {
        "message": f"Submission graded successfully! Grade: {sub.grade}/{sub.assignment.max_points}",
        "submission_id": sub.id,
        "grade": sub.grade,
        "feedback": sub.feedback,
        "status": sub.status
    }

@router.get("/my-submissions")
def get_my_submissions(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Student can view all their submitted assignments and grades."""
    subs = db.query(models.Submission).filter(
        models.Submission.student_id == current_user.id
    ).order_by(models.Submission.submitted_at.desc()).all()

    return [
        {
            "submission_id": s.id,
            "assignment_id": s.assignment_id,
            "assignment_title": s.assignment.title if s.assignment else "Assignment",
            "subject": s.assignment.subject if s.assignment else "General",
            "max_points": s.assignment.max_points if s.assignment else 100,
            "grade": s.grade,
            "feedback": s.feedback,
            "status": s.status,
            "file_url": s.file_url,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None
        }
        for s in subs
    ]
