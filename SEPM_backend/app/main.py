from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path
from . import models, database, auth as auth_utils
from .database import engine, SessionLocal
from .storage import UPLOAD_DIR
from .routers import auth, materials, chat, attendance, assignments, announcements, whiteboard, admin, courses

# Automatically run migrations and ensure all tables exist in SQLite
database.run_migrations()
models.Base.metadata.create_all(bind=engine)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "Front_end"

def bootstrap_initial_admin():
    username = os.getenv("INITIAL_ADMIN_USERNAME")
    password = os.getenv("INITIAL_ADMIN_PASSWORD")
    if not username and not password:
        return
    if not username or not password:
        raise RuntimeError("Both INITIAL_ADMIN_USERNAME and INITIAL_ADMIN_PASSWORD must be configured.")
    if len(password) < 16:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD must be at least 16 characters.")

    db = SessionLocal()
    try:
        if db.query(models.User).count() != 0:
            return
        db.add(models.User(
            username=username.strip(),
            hashed_password=auth_utils.get_password_hash(password),
            role=models.UserRole.admin,
            full_name="System Administrator"
        ))
        db.commit()
    finally:
        db.close()

bootstrap_initial_admin()

app = FastAPI(
    title="College & Classroom Management API",
    description="Backend API supporting Classroom streams, Google Drive notes, WhatsApp chat, Whiteboard, Attendance, and Admin controls.",
    version="2.0.0"
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:3000,http://localhost:3000"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for static file access (PDFs, docs, images, whiteboard previews)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include all feature routers
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(materials.router)
app.include_router(assignments.router)
app.include_router(announcements.router)
app.include_router(whiteboard.router)
app.include_router(attendance.router)
app.include_router(chat.router)
app.include_router(admin.router)

@app.get("/healthz", include_in_schema=False)
def health_check():
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
def read_root():
    return FileResponse(FRONTEND_DIR / "index.html")

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")