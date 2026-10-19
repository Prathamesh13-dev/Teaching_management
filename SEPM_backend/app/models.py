from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

# --- CORE MODELS ---

class UserRole(str, enum.Enum):
    teacher = "teacher"
    student = "student"
    admin = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.student)

    materials = relationship("ClassMaterial", back_populates="uploader")
    attendances = relationship("Attendance", back_populates="student")

class ClassMaterial(Base):
    __tablename__ = "class_materials"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    subject = Column(String, index=True) 
    file_url = Column(String) 
    is_public = Column(Boolean, default=True) 
    uploaded_by_id = Column(Integer, ForeignKey("users.id"))
    time_created = Column(DateTime(timezone=True), server_default=func.now())

    uploader = relationship("User", back_populates="materials")

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String) 
    
    student = relationship("User", back_populates="attendances")

# --- NEW CHAT FEATURE MODELS ---

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("study_groups.id"))
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

class StudyGroup(Base):
    __tablename__ = "study_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) 
    description = Column(String, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    time_created = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("Message", back_populates="group")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    sender_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("study_groups.id"))
    time_sent = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("StudyGroup", back_populates="messages")
    sender = relationship("User")