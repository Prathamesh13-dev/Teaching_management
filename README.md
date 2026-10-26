# 🎓 College & Classroom Management Portal (SEPM Project)

A complete, role-based educational and classroom collaboration web application designed for students, faculty, and administrators. Built with a modern, high-performance **FastAPI (Python)** backend and a responsive, aesthetic **Vanilla HTML/CSS/JavaScript** frontend with offline support.

---

## 🌟 Product References & Workflows

The portal blends core workflows inspired by leading educational platforms into a cohesive academic hub:

1. **Google Classroom**
   - **Stream**: Broadcast announcements with priority tags (Normal, Important, Urgent), view course banners, and check upcoming deadlines.
   - **Class enrollment**: Teachers create classes and share their generated class code; students enter that code to enroll.
   - **Assignments**: Teachers post coursework with due dates and maximum marks; students upload submissions with notes; teachers review submissions, input numerical grades, and return feedback comments.

2. **WhatsApp**
   - **Real-Time Group Chat**: Study groups with live WebSocket messaging and automatic database persistence.
   - **Message History**: Full chat history loaded instantly upon opening any group.
   - **Direct 1-on-1 Messaging**: Private messaging between students and classmates or instructors.
   - **Moderation**: Faculty and administrators can remove inappropriate messages or delete study groups.

3. **Digital Whiteboard**
   - **Interactive Canvas**: Multi-tool drawing suite including Freehand Pen, Straight Line, Rectangle, Circle, and Eraser.
   - **Customizable Palettes**: Color swatches, custom color picker, and brush width slider (1px–24px).
   - **Lesson Reference Library**: Teachers can save their lesson boards with title and subject; students can access, browse, and re-load saved boards directly onto the canvas as study aids.
   - **Export**: Instant PNG image export for notes and assignments.

4. **Google Drive / Files**
   - **Course Materials Explorer**: Filter by subject/course, search notes by keyword, and download resources.
   - **Inline Document Preview**: Built-in modal viewer for text documents, images, and PDF lecture notes.
   - **Offline Mode**: IndexedDB caching allows students to save documents locally and access them without an active internet connection.

5. **Attendance Apps**
   - **Student Attendance Analytics**: Dynamic attendance percentage gauge (e.g., `85.7%`), mandatory 75% threshold standing indicator, breakdown of Present, Late, and Absent sessions, and complete date-wise history.
   - **Teacher Roster & Class Summaries**: Date picker, rapid "Check All Present" shortcut, per-student status radio pills with faculty notes, and class-wide attendance averages.

---

## 👥 Role Descriptions & Permissions Matrix

The portal implements strict, server-side Role-Based Access Control (RBAC) enforced across all API endpoints:

| Feature / Action | 🎓 Student | 👨‍🏫 Teacher | 🛡️ Administrator |
| :--- | :---: | :---: | :---: |
| **Browse & Preview Class Materials** | ✅ Public | ✅ All | ✅ All |
| **Download & Save Notes Offline** | ✅ | ✅ | ✅ |
| **Upload Class Materials** | ❌ | ✅ | ✅ |
| **Delete Class Materials** | ❌ | ✅ (Own) | ✅ (Any) |
| **View Announcements & Deadlines** | ✅ | ✅ | ✅ |
| **Post Announcements** | ❌ | ✅ | ✅ |
| **Submit Assignments** | ✅ | ❌ | ❌ |
| **Create & Manage Assignments** | ❌ | ✅ | ✅ |
| **Grade Submissions & Give Feedback** | ❌ | ✅ | ✅ |
| **Participate in Study Group Chat** | ✅ | ✅ | ✅ |
| **Send 1-on-1 Direct Messages** | ✅ | ✅ | ✅ |
| **Create Study Groups** | ✅ | ✅ | ✅ |
| **Moderate Messages / Delete Groups** | ❌ (Own only) | ✅ | ✅ |
| **Use Interactive Whiteboard** | ✅ | ✅ | ✅ |
| **Save Whiteboard as Study Lesson** | ❌ | ✅ | ✅ |
| **View Personal Attendance & %** | ✅ | ✅ | ✅ |
| **Mark Class Attendance for Date** | ❌ | ✅ | ✅ |
| **Class Attendance Summary Stats** | ❌ | ✅ | ✅ |
| **User & Role Management** | ❌ | ❌ | ✅ |
| **System Governance & Metrics** | ❌ | ❌ | ✅ |

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- Python 3.10+ installed
- Web browser (Chrome, Edge, Firefox, or Safari)

### 2. Backend Setup
Navigate to the `SEPM_backend` directory and activate the existing virtual environment:

```powershell
# In PowerShell:
cd SEPM_backend
.\venv\Scripts\Activate.ps1
```

Install dependencies if setting up on a new environment:
```powershell
pip install -r requirements.txt
```

### 3. Database Migration & Demo Data Seeding
Run the included seed script to apply automatic schema migrations and populate realistic demo records:
```powershell
python seed_data.py
```

### 4. Start the Backend API Server
Launch the FastAPI development server:
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
The API and interactive Swagger documentation will be available at:
- **Portal**: `http://127.0.0.1:8001/`
- **API health check**: `http://127.0.0.1:8001/healthz`
- **Interactive Swagger Docs**: `http://127.0.0.1:8001/docs`

### 5. Launch the Frontend
You can open `Front_end/index.html` directly in your browser, or serve it using Python:
```powershell
python -m http.server 3000 --directory Front_end
```
Then visit: `http://127.0.0.1:3000/index.html`

## ☁️ Deploy from GitHub

The root `render.yaml` configures a free Render web service that serves the frontend and FastAPI API from the same origin. The free plan has no persistent disk, so its SQLite database and uploaded files are temporary and may be lost when the service restarts or is redeployed. Free services can also spin down while idle.

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint**, connect this GitHub repository, and deploy the `render.yaml` blueprint.
3. When prompted, set `INITIAL_ADMIN_USERNAME` and a unique `INITIAL_ADMIN_PASSWORD` of at least 16 characters. These values are used only to create the first administrator when the database is empty.
4. After deployment, open the service URL. The health check is available at `/healthz`; API documentation is at `/docs`.

Keep `SECRET_KEY` generated by Render and do not commit credentials or environment files. Public registration creates student accounts only; an administrator provisions teacher accounts. Do not run the demo seed script on the public service because its sample credentials are intentionally for local evaluation. For durable production data and uploads, use a paid persistent disk or an external managed database and object-storage service.

To deploy on another host, set `SECRET_KEY`, `DATABASE_URL`, `UPLOAD_DIR`, `INITIAL_ADMIN_USERNAME`, and `INITIAL_ADMIN_PASSWORD`; the host must provide persistent storage for the configured SQLite database and uploads.

---

## 🔑 Pre-Configured Demo Accounts

For instant student project evaluation, the landing page includes **1-Click Quick Demo Login** buttons:

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Student** | `student_demo` | `student123` | Aarav Patel (Sample submitted assignment & 100% attendance) |
| **Teacher** | `teacher_demo` | `teacher123` | Prof. Rajesh Sharma (Course creator, attendance marker) |
| **Admin** | `admin` | `admin123` | System Administrator (Full platform governance) |

These sample accounts are created only by running `seed_data.py` for local evaluation. Do not seed these public sample credentials in a production deployment. The deployed service provisions its first administrator from the private `INITIAL_ADMIN_*` environment variables.

---

## 🧪 Automated Testing & Verification

A comprehensive automated test suite is included in `SEPM_backend/test_api_endpoints.py`. Run it at any time:

```powershell
cd SEPM_backend
python test_api_endpoints.py
```

The test suite validates:
- User authentication and role retrieval (`/me`)
- Course materials query and subject filtering
- Assignments query and student submission status
- Attendance calculation and percentage accuracy
- Announcements feed and priority flags
- Whiteboard stroke storage and retrieval
- Study group message persistence and direct messaging
- Admin statistics and RBAC permission barriers (blocking unauthorized roles with `403 Forbidden`)

---

## 🛠️ Summary of Improvements & Bug Fixes

1. **Fixed Static File Serving Bug**: `app.main:app` previously lacked a `StaticFiles` mount for `uploads/`. Added `app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")` so students and teachers can preview and download notes and assignment submissions without 404 errors.
2. **Fixed Undefined Course Model**: Fixed an unhandled `models.Course` reference in `materials.py` by implementing the `Course` model with teacher assignment and relationship links.
3. **Unified Token Authentication**: Standardized JWT token generation and verification using `python-jose`, extending demo session tokens to 24 hours to prevent mid-demonstration logouts.
4. **Google Classroom Assignments Engine**:
   - Built `Assignment` and `Submission` database models.
   - Built complete REST endpoints for assignment creation, file submission, submission review, and numerical grading with faculty feedback.
5. **WhatsApp-Style Chat & Message History**:
   - Fixed chat message history: selecting any study group now immediately loads previous conversations from SQLite.
   - Added 1-on-1 private messaging between students and faculty.
   - Added group and message moderation controls for faculty and admins.
   - Enhanced WebSocket connection manager with graceful reconnection and REST fallback.
6. **Digital Whiteboard**:
   - Implemented an interactive HTML5 canvas supporting freehand drawing, lines, rectangles, circles, and erasers.
   - Added palette swatches, stroke thickness controls, and image export.
   - Added server-side saving for lesson boards so students can open and study instructors' lecture diagrams.
7. **Comprehensive Attendance Module**:
   - Implemented personal attendance percentage calculation and standing indicator for students.
   - Implemented date-based attendance marking and class-wide analytics for teachers.
8. **Admin Control Center**:
   - Added system statistics overview (user counts, content metrics, attendance rates).
   - Added user directory with dynamic role management and deletion safeguards (preventing self-deletion or demotion of the last admin).
9. **UI / UX Polish**:
   - Added 1-Click Quick Demo Login buttons to `index.html`.
   - Redesigned `dashboard.html` with responsive sidebar navigation, modern typography, glassmorphism cards, toast notifications, and modal dialogs.
   - Updated Service Worker cache to `v2` for reliable offline application shell caching.
