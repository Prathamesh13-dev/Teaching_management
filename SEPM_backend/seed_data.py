import os
import json
from datetime import datetime, date, timedelta
from app.database import engine, SessionLocal, Base, run_migrations
from app import models, auth

def seed_database():
    # Run column migrations on existing database
    run_migrations()
    # Create all tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("[*] Seeding College Management Portal database...")

        # 1. Accounts to seed
        accounts = [
            ("admin", "admin123", models.UserRole.admin, "System Administrator", "admin@college.edu"),
            ("teacher_demo", "teacher123", models.UserRole.teacher, "Prof. Rajesh Sharma", "teacher@college.edu"),
            ("student_demo", "student123", models.UserRole.student, "Aarav Patel", "student@college.edu"),
            ("priya_sharma", "student123", models.UserRole.student, "Priya Sharma", "priya@college.edu"),
            ("rohit_verma", "student123", models.UserRole.student, "Rohit Verma", "rohit@college.edu"),
        ]

        user_map = {}
        for username, password, role, full_name, email in accounts:
            u = db.query(models.User).filter(models.User.username == username).first()
            if not u:
                u = models.User(
                    username=username,
                    hashed_password=auth.get_password_hash(password),
                    role=role,
                    full_name=full_name,
                    email=email
                )
                db.add(u)
                db.commit()
                db.refresh(u)
                print(f"  + Created user: {username} ({role.value})")
            else:
                # Update role if needed
                u.role = role
                u.full_name = full_name
                db.commit()
            user_map[username] = u

        # Get existing users
        for u in db.query(models.User).all():
            user_map[u.username] = u

        teacher = user_map.get("teacher_demo") or user_map.get("Prathamesh")
        student = user_map.get("student_demo") or user_map.get("sujal")
        admin = user_map.get("admin")

        # 2. Seed Courses
        courses_data = [
            ("Software Engineering & Project Management", "SEPM-301", "Section A", "Core software lifecycles, Agile scrum, sprint planning, and architecture design.", "sepm301", "indigo"),
            ("Database Management Systems", "DBMS-202", "Section B", "Relational database design, normal forms, indexing, and SQL queries.", "dbms202", "teal"),
            ("Cloud Computing & DevOps", "CC-401", "Section C", "Virtualization, containerization, Docker, Kubernetes, and CI/CD automation.", "cc401", "emerald"),
            ("Artificial Intelligence & Machine Learning", "AIML-501", "Section A", "Supervised and unsupervised learning, neural networks, and computer vision.", "aiml501", "coral")
        ]
        course_map = {}
        for name, code, sec, desc, j_code, theme in courses_data:
            c = db.query(models.Course).filter(models.Course.code == code).first()
            if not c:
                c = models.Course(
                    name=name, code=code, section=sec, description=desc,
                    join_code=j_code, color_theme=theme, teacher_id=teacher.id
                )
                db.add(c)
                db.commit()
                db.refresh(c)
                print(f"  + Created course: {name} (Join Code: {j_code})")
            else:
                # Update attributes
                c.section = sec
                c.join_code = j_code
                c.color_theme = theme
                db.commit()
            course_map[code] = c

        # 2b. Seed Initial Enrollments for multiple classes
        # student_demo enrolls in SEPM-301 and DBMS-202 initially
        students_list = db.query(models.User).filter(models.User.role == models.UserRole.student).all()
        for s in students_list:
            # All students enroll in SEPM-301
            e1 = db.query(models.Enrollment).filter(models.Enrollment.student_id == s.id, models.Enrollment.course_id == course_map["SEPM-301"].id).first()
            if not e1:
                db.add(models.Enrollment(student_id=s.id, course_id=course_map["SEPM-301"].id))
            
            # student_demo and priya_sharma also enroll in DBMS-202
            if s.username in ["student_demo", "priya_sharma", "sujal"]:
                e2 = db.query(models.Enrollment).filter(models.Enrollment.student_id == s.id, models.Enrollment.course_id == course_map["DBMS-202"].id).first()
                if not e2:
                    db.add(models.Enrollment(student_id=s.id, course_id=course_map["DBMS-202"].id))
        db.commit()
        print("  + Seeded multi-class enrollments")

        # 3. Seed Announcements
        announcements_data = [
            ("SEPM Project Sprint 2 Submission", "Please ensure your Sprint 2 backlog, UML sequence diagrams, and GitHub repository links are submitted before Friday at 5:00 PM.", "Important"),
            ("Welcome to Fall Semester 2026", "Welcome students! All lecture notes, whiteboard lesson boards, and assignments will be posted on this portal. Check your attendance regularly.", "Normal"),
            ("Upcoming Workshop: Agile Project Management with Jira", "Join us this Thursday at 2:00 PM for a hands-on session on Agile estimation and sprint retrospectives.", "Normal")
        ]
        if db.query(models.Announcement).count() == 0:
            for title, content, priority in announcements_data:
                a = models.Announcement(
                    title=title,
                    content=content,
                    priority=priority,
                    posted_by_id=teacher.id
                )
                db.add(a)
            db.commit()
            print("  + Seeded announcements")

        # 4. Seed Class Materials
        os.makedirs("uploads", exist_ok=True)
        sample_doc_path = "uploads/SEPM_Unit1_Lecture_Notes.txt"
        if not os.path.exists(sample_doc_path):
            with open(sample_doc_path, "w", encoding="utf-8") as f:
                f.write("SOFTWARE ENGINEERING & PROJECT MANAGEMENT\nUnit 1: Introduction to Agile & Scrum\n\n1. Agile Manifesto Principles\n2. Sprint Planning & Velocity\n3. Scrum Ceremonies: Standup, Review, Retrospective\n4. Requirements Engineering & User Story Mapping\n")

        sample_agile_path = "uploads/Agile_Scrum_Playbook.txt"
        if not os.path.exists(sample_agile_path):
            with open(sample_agile_path, "w", encoding="utf-8") as f:
                f.write("AGILE SCRUM PLAYBOOK\n\n- Definition of Done (DoD)\n- Acceptance Criteria Guidelines\n- Burndown Charts & Risk Matrices\n")

        materials_to_seed = [
            ("Unit 1: Agile Architecture & Methodologies", "Software Engineering", sample_doc_path),
            ("Agile Scrum Team Playbook & Roles", "Software Engineering", sample_agile_path)
        ]
        for m_title, m_subj, m_path in materials_to_seed:
            if not db.query(models.ClassMaterial).filter(models.ClassMaterial.title == m_title).first():
                m = models.ClassMaterial(
                    title=m_title,
                    subject=m_subj,
                    file_url=m_path,
                    file_type="document",
                    is_public=True,
                    uploaded_by_id=teacher.id,
                    course_id=course_map["SEPM-301"].id
                )
                db.add(m)
        db.commit()
        print("  + Seeded class materials")

        # 5. Seed Assignments
        if db.query(models.Assignment).count() == 0:
            a1 = models.Assignment(
                title="Sprint 1: Software Requirements Specification (SRS)",
                description="Draft the SRS document following IEEE 830 standard. Include functional and non-functional requirements, use cases, and persona definitions.",
                subject="Software Engineering",
                due_date=(date.today() + timedelta(days=5)).isoformat(),
                max_points=100,
                created_by_id=teacher.id
            )
            a2 = models.Assignment(
                title="UML Domain Model & Class Diagram",
                description="Design comprehensive UML class and sequence diagrams illustrating user authentication, role-based workflows, and database entities.",
                subject="Software Engineering",
                due_date=(date.today() + timedelta(days=12)).isoformat(),
                max_points=50,
                created_by_id=teacher.id
            )
            db.add_all([a1, a2])
            db.commit()
            db.refresh(a1)
            db.refresh(a2)
            print("  + Seeded assignments")

            # Seed a sample submission for student_demo
            sample_sub_path = "uploads/assignments/student_demo_srs_v1.txt"
            os.makedirs("uploads/assignments", exist_ok=True)
            with open(sample_sub_path, "w", encoding="utf-8") as f:
                f.write("SRS Document - Team Alpha\nProject: College Management Portal\nAuthor: Aarav Patel\n\n1. Functional Scope\n2. Security Requirements\n3. Data Flow Diagram\n")

            sub = models.Submission(
                assignment_id=a1.id,
                student_id=student.id,
                file_url=sample_sub_path,
                student_notes="Attached our team's completed SRS draft with all functional modules.",
                grade=94.0,
                feedback="Excellent work on the user stories and non-functional requirements. The security matrix is well structured.",
                status="Graded"
            )
            db.add(sub)
            db.commit()
            print("  + Seeded sample graded submission")

        # 6. Seed Attendance over last 6 instructional days
        students = db.query(models.User).filter(models.User.role == models.UserRole.student).all()
        existing_att_count = db.query(models.Attendance).count()
        if existing_att_count < 10:
            today = date.today()
            dates = [(today - timedelta(days=i)).isoformat() for i in range(1, 8) if (today - timedelta(days=i)).weekday() < 5] # Weekdays
            for d in dates[:5]:
                for idx, s in enumerate(students):
                    # Make most students present, occasional absent or late
                    status = "Present"
                    if idx % 3 == 0 and d == dates[2]:
                        status = "Late"
                    elif idx % 4 == 0 and d == dates[4]:
                        status = "Absent"

                    existing = db.query(models.Attendance).filter(
                        models.Attendance.student_id == s.id,
                        models.Attendance.date == d
                    ).first()
                    if not existing:
                        att = models.Attendance(
                            student_id=s.id,
                            date=d,
                            status=status,
                            marked_by_id=teacher.id,
                            notes="Regular lecture attendance"
                        )
                        db.add(att)
            db.commit()
            print("  + Seeded attendance history over 5 dates")

        # 7. Seed Whiteboard Lesson
        if db.query(models.WhiteboardLesson).count() == 0:
            sample_board_data = json.dumps({
                "lines": [
                    {"tool": "pen", "color": "#4f46e5", "size": 3, "points": [{"x": 100, "y": 80}, {"x": 300, "y": 80}, {"x": 300, "y": 180}, {"x": 100, "y": 180}, {"x": 100, "y": 80}]},
                    {"tool": "pen", "color": "#10b981", "size": 3, "points": [{"x": 400, "y": 80}, {"x": 600, "y": 80}, {"x": 600, "y": 180}, {"x": 400, "y": 180}, {"x": 400, "y": 80}]},
                    {"tool": "pen", "color": "#f59e0b", "size": 3, "points": [{"x": 250, "y": 260}, {"x": 450, "y": 260}, {"x": 450, "y": 360}, {"x": 250, "y": 360}, {"x": 250, "y": 260}]},
                    {"tool": "pen", "color": "#6366f1", "size": 2, "points": [{"x": 200, "y": 180}, {"x": 300, "y": 260}]},
                    {"tool": "pen", "color": "#6366f1", "size": 2, "points": [{"x": 500, "y": 180}, {"x": 400, "y": 260}]}
                ],
                "labels": [
                    {"text": "Frontend Client (SPA)", "x": 120, "y": 130, "color": "#1e293b"},
                    {"text": "FastAPI Microservice", "x": 420, "y": 130, "color": "#1e293b"},
                    {"text": "SQLite / PostgreSQL DB", "x": 270, "y": 310, "color": "#1e293b"}
                ]
            })

            w = models.WhiteboardLesson(
                title="Lecture 3: Microservices & Three-Tier Architecture",
                subject="Software Engineering",
                board_data=sample_board_data,
                preview_image=None,
                saved_by_id=teacher.id
            )
            db.add(w)
            db.commit()
            print("  + Seeded digital whiteboard lesson")

        # 8. Seed Study Group & Messages
        if db.query(models.StudyGroup).count() == 0:
            g = models.StudyGroup(
                name="SEPM Project Collaboration & Q&A",
                description="Official study & project discussion group for Software Engineering Section A.",
                created_by_id=teacher.id
            )
            db.add(g)
            db.commit()
            db.refresh(g)

            m1 = models.Message(
                content="Hello everyone! Welcome to the SEPM collaboration chat. Feel free to ask questions about your sprint deliverables here.",
                sender_id=teacher.id,
                group_id=g.id
            )
            m2 = models.Message(
                content="Thank you Professor! We had a quick question regarding the UML class diagram format. Should we include private method signatures?",
                sender_id=student.id,
                group_id=g.id
            )
            m3 = models.Message(
                content="Yes Aarav, please include public and protected interfaces with their return types as per standard UML 2.5 conventions.",
                sender_id=teacher.id,
                group_id=g.id
            )
            db.add_all([m1, m2, m3])
            db.commit()
            print("  + Seeded study group and discussion messages")

        print("[OK] Database seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error during seeding: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
