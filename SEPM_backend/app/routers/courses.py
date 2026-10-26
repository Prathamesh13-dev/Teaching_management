from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import secrets
import string
from .. import models, dependencies

router = APIRouter(prefix="/courses", tags=["Classes & Enrollments (Google Classroom)"])

def generate_join_code(length: int = 6) -> str:
    chars = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def generate_unique_join_code(db: Session) -> str:
    join_code = generate_join_code()
    while db.query(models.Course).filter(models.Course.join_code == join_code).first():
        join_code = generate_join_code()
    return join_code

def ensure_join_codes(db: Session, courses: list[models.Course]) -> None:
    changed = False
    for course in courses:
        if not course.join_code:
            course.join_code = generate_unique_join_code(db)
            changed = True
    if changed:
        db.commit()

def require_student(current_user: models.User) -> None:
    if current_user.role != models.UserRole.student:
        raise HTTPException(status_code=403, detail="Only students can enroll in a class.")

class CourseCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    code: Optional[str] = None # e.g. "SEPM-301"
    section: Optional[str] = "Section A"
    description: Optional[str] = None
    join_code: Optional[str] = None
    color_theme: Optional[str] = "indigo" # indigo, teal, emerald, coral, amber, violet

class JoinCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)

@router.get("/my-classes")
def get_my_classes(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Returns the list of classes the user is enrolled in (for students) or teaches (for faculty)."""
    if current_user.role == models.UserRole.student:
        # Enrolled classes for this student
        enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == current_user.id).all()
        enrolled_course_ids = [e.course_id for e in enrollments]
        courses = db.query(models.Course).filter(models.Course.id.in_(enrolled_course_ids)).all()
    elif current_user.role == models.UserRole.teacher:
        # Classes taught by this teacher
        courses = db.query(models.Course).filter(models.Course.teacher_id == current_user.id).all()
    else:
        # Admin sees all classes
        courses = db.query(models.Course).all()

    if current_user.role in (models.UserRole.teacher, models.UserRole.admin):
        ensure_join_codes(db, courses)

    results = []
    for c in courses:
        enrolled_count = db.query(models.Enrollment).filter(models.Enrollment.course_id == c.id).count()
        mat_count = db.query(models.ClassMaterial).filter(models.ClassMaterial.course_id == c.id).count()
        asgn_count = db.query(models.Assignment).filter(models.Assignment.course_id == c.id).count()
        ann_count = db.query(models.Announcement).filter(models.Announcement.course_id == c.id).count()

        results.append({
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "section": c.section or "Section A",
            "description": c.description,
            "join_code": c.join_code if (
                current_user.role == models.UserRole.admin
                or (current_user.role == models.UserRole.teacher and c.teacher_id == current_user.id)
            ) else None,
            "color_theme": c.color_theme or "indigo",
            "teacher_id": c.teacher_id,
            "teacher_name": c.teacher.username if c.teacher else "Faculty Instructor",
            "teacher_full_name": (c.teacher.full_name or c.teacher.username) if c.teacher else "Faculty Instructor",
            "enrolled_students_count": enrolled_count,
            "materials_count": mat_count,
            "assignments_count": asgn_count,
            "announcements_count": ann_count,
            "is_enrolled": True
        })
    return results

@router.get("/available")
def get_available_classes(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Lists all courses in the college catalog with enrollment status for students."""
    all_courses = db.query(models.Course).order_by(models.Course.name.asc()).all()
    
    enrolled_ids = set()
    if current_user.role == models.UserRole.student:
        my_enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == current_user.id).all()
        enrolled_ids = set(e.course_id for e in my_enrollments)

    results = []
    for c in all_courses:
        enrolled_count = db.query(models.Enrollment).filter(models.Enrollment.course_id == c.id).count()
        results.append({
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "section": c.section or "Section A",
            "description": c.description,
            "color_theme": c.color_theme or "indigo",
            "teacher_name": (c.teacher.full_name or c.teacher.username) if c.teacher else "Faculty Instructor",
            "enrolled_students_count": enrolled_count,
            "is_enrolled": c.id in enrolled_ids
        })
    return results

@router.post("/join-by-code")
def join_class_by_code(
    body: JoinCodeRequest,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Students can join any class instantly by entering its Google Classroom style class join code."""
    require_student(current_user)
    clean_code = body.code.strip().lower()
    if not clean_code:
        raise HTTPException(status_code=400, detail="Please enter a valid class code")

    course = db.query(models.Course).filter(models.Course.join_code.ilike(clean_code)).first()

    if not course:
        raise HTTPException(status_code=404, detail="No class found matching this code. Please check with your teacher.")

    # Check if already enrolled
    existing = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == current_user.id,
        models.Enrollment.course_id == course.id
    ).first()

    if existing:
        return {
            "message": f"You are already enrolled in {course.name} ({course.section})!",
            "course_id": course.id,
            "course_name": course.name
        }

    enrollment = models.Enrollment(student_id=current_user.id, course_id=course.id)
    db.add(enrollment)
    db.commit()

    return {
        "message": f"Successfully enrolled in {course.name} ({course.section})!",
        "course_id": course.id,
        "course_name": course.name
    }

@router.post("/{course_id}/enroll")
def enroll_in_course(
    course_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """One-click enrollment for a student into a class."""
    require_student(current_user)
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Class not found")

    existing = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == current_user.id,
        models.Enrollment.course_id == course_id
    ).first()

    if existing:
        return {"message": "Already enrolled", "course_id": course.id}

    enrollment = models.Enrollment(student_id=current_user.id, course_id=course_id)
    db.add(enrollment)
    db.commit()

    return {
        "message": f"Successfully enrolled in {course.name}!",
        "course_id": course.id,
        "course_name": course.name
    }

@router.delete("/{course_id}/unenroll")
def unenroll_from_course(
    course_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Students can unenroll from a class."""
    require_student(current_user)
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == current_user.id,
        models.Enrollment.course_id == course_id
    ).first()

    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment record not found")

    db.delete(enrollment)
    db.commit()
    return {"message": "Successfully unenrolled from the class."}

@router.post("/create")
def create_course(
    body: CourseCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers/Admins can create a new class (like Google Classroom '+ Create Class')."""
    join_code = body.join_code.strip().lower() if body.join_code else None
    if join_code and db.query(models.Course).filter(models.Course.join_code.ilike(join_code)).first():
        raise HTTPException(status_code=409, detail="That class code is already in use.")
    join_code = join_code or generate_unique_join_code(db)

    color_palette = ["indigo", "teal", "emerald", "coral", "amber", "violet"]
    theme = body.color_theme if body.color_theme in color_palette else "indigo"

    new_course = models.Course(
        name=body.name.strip(),
        code=body.code.strip() if body.code else None,
        section=body.section.strip() if body.section else "Section A",
        description=body.description.strip() if body.description else None,
        join_code=join_code,
        color_theme=theme,
        teacher_id=current_user.id
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)

    return {
        "message": f"Class '{new_course.name}' created successfully!",
        "id": new_course.id,
        "name": new_course.name,
        "section": new_course.section,
        "join_code": new_course.join_code
    }

@router.get("/{course_id}")
def get_course_details(
    course_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Fetches details for a specific class including enrolled classmates."""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Class not found")

    is_teacher = current_user.role == models.UserRole.teacher and course.teacher_id == current_user.id
    is_admin = current_user.role == models.UserRole.admin
    is_enrolled = db.query(models.Enrollment).filter(
        models.Enrollment.course_id == course_id,
        models.Enrollment.student_id == current_user.id
    ).first() is not None
    if not (is_teacher or is_admin or is_enrolled):
        raise HTTPException(status_code=403, detail="You are not a member of this class.")
    if (is_teacher or is_admin) and not course.join_code:
        ensure_join_codes(db, [course])

    enrollments = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id).all()
    classmates = [
        {
            "id": e.student.id,
            "username": e.student.username,
            "full_name": e.student.full_name or e.student.username,
            "email": e.student.email,
            "enrolled_at": e.enrolled_at.isoformat() if e.enrolled_at else None
        }
        for e in enrollments if e.student
    ]

    return {
        "id": course.id,
        "name": course.name,
        "code": course.code,
        "section": course.section or "Section A",
        "description": course.description,
        "join_code": course.join_code if is_teacher or is_admin else None,
        "color_theme": course.color_theme or "indigo",
        "teacher_id": course.teacher_id,
        "teacher_name": (course.teacher.full_name or course.teacher.username) if course.teacher else "Instructor",
        "teacher_email": course.teacher.email if course.teacher else "",
        "classmates": classmates,
        "total_enrolled": len(classmates)
    }

@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Teachers can delete their own class; Admins can delete any class."""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Class not found")

    if current_user.role != models.UserRole.admin and course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete classes you teach.")

    db.delete(course)
    db.commit()
    return {"message": f"Class '{course.name}' deleted successfully."}
