from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Boolean, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

# --- CORE USER ROLES ---

class UserRole(str, enum.Enum):
    teacher = "teacher"
    student = "student"
    admin = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.student, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    time_created = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    materials = relationship("ClassMaterial", back_populates="uploader", foreign_keys="ClassMaterial.uploaded_by_id")
    attendances = relationship("Attendance", back_populates="student", foreign_keys="Attendance.student_id")
    assignments_created = relationship("Assignment", back_populates="creator", foreign_keys="Assignment.created_by_id")
    submissions = relationship("Submission", back_populates="student", foreign_keys="Submission.student_id")
    announcements = relationship("Announcement", back_populates="author", foreign_keys="Announcement.posted_by_id")
    whiteboards = relationship("WhiteboardLesson", back_populates="creator", foreign_keys="WhiteboardLesson.saved_by_id")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")

# --- COURSES / CLASSES (Google Classroom Reference) ---

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    code = Column(String, nullable=True) # e.g. SEPM-301
    section = Column(String, default="Section A") # Section A, Fall 2026
    description = Column(String, nullable=True)
    join_code = Column(String, unique=True, index=True, nullable=True) # e.g. sepm301
    color_theme = Column(String, default="indigo") # indigo, teal, emerald, coral, amber, violet
    teacher_id = Column(Integer, ForeignKey("users.id"))
    time_created = Column(DateTime(timezone=True), server_default=func.now())

    teacher = relationship("User")
    materials = relationship("ClassMaterial", back_populates="course")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course")
    announcements = relationship("Announcement", back_populates="course")

# --- ENROLLMENTS (Students enrolled in multiple classes) ---

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

# --- CLASS MATERIALS / NOTES (Google Drive / Files Reference) ---

class ClassMaterial(Base):
    __tablename__ = "class_materials"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    subject = Column(String, index=True, nullable=False)
    file_url = Column(String, nullable=False)
    file_type = Column(String, default="document") # pdf, image, doc, etc.
    is_public = Column(Boolean, default=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"))
    time_created = Column(DateTime(timezone=True), server_default=func.now())

    uploader = relationship("User", back_populates="materials")
    course = relationship("Course", back_populates="materials")

# --- ATTENDANCE (Attendance Apps Reference) ---

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    date = Column(String, index=True, nullable=False) # Format: YYYY-MM-DD
    status = Column(String, nullable=False) # Present, Absent, Late
    marked_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(String, nullable=True)
    time_created = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("User", back_populates="attendances", foreign_keys=[student_id])
    marker = relationship("User", foreign_keys=[marked_by_id])
    course = relationship("Course", foreign_keys=[course_id])

# --- ANNOUNCEMENTS (Google Classroom Reference) ---

class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String, default="Normal") # Normal, Important, Urgent
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    posted_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    time_created = Column(DateTime(timezone=True), server_default=func.now())

    author = relationship("User", back_populates="announcements")
    course = relationship("Course", back_populates="announcements")

# --- ASSIGNMENTS & SUBMISSIONS (Google Classroom Reference) ---

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=False)
    subject = Column(String, index=True, nullable=False)
    due_date = Column(String, nullable=False) # YYYY-MM-DD or formatted timestamp
    max_points = Column(Integer, default=100)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    attachment_url = Column(String, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    time_created = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User", back_populates="assignments_created")
    course = relationship("Course", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_url = Column(String, nullable=False)
    student_notes = Column(Text, nullable=True)
    grade = Column(Float, nullable=True) # e.g. 92.5
    feedback = Column(Text, nullable=True)
    status = Column(String, default="Submitted") # Submitted, Graded, Returned
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    graded_at = Column(DateTime(timezone=True), nullable=True)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", back_populates="submissions")

# --- DIGITAL WHITEBOARD (Digital Whiteboard Apps Reference) ---

class WhiteboardLesson(Base):
    __tablename__ = "whiteboard_lessons"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    subject = Column(String, index=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    board_data = Column(Text, nullable=False) # JSON serialization of strokes / shapes
    preview_image = Column(Text, nullable=True) # Data URL thumbnail or exported snapshot
    saved_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    time_created = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User", back_populates="whiteboards")
    course = relationship("Course", foreign_keys=[course_id])

# --- CHAT & STUDY GROUPS (WhatsApp Reference) ---

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("study_groups.id"))
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

class StudyGroup(Base):
    __tablename__ = "study_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    time_created = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("Message", back_populates="group", cascade="all, delete-orphan")
    creator = relationship("User")
    course = relationship("Course", foreign_keys=[course_id])

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("study_groups.id"), nullable=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=True) # For 1-on-1 direct messages
    is_direct = Column(Boolean, default=False)
    time_sent = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("StudyGroup", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])