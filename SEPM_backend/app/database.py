from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
import sqlite3
import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sepm_project.db")
database_url = make_url(SQLALCHEMY_DATABASE_URL)
is_sqlite = database_url.get_backend_name() == "sqlite"
if is_sqlite and database_url.database not in (None, "", ":memory:"):
    database_path = os.path.abspath(os.path.expanduser(database_url.database))
    os.makedirs(os.path.dirname(database_path), exist_ok=True)

engine_options = {"connect_args": {"check_same_thread": False}} if is_sqlite else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def run_migrations():
    """Safely adds missing columns and tables to SQLite if they already exist."""
    if not is_sqlite or database_url.database in (None, "", ":memory:"):
        return
    db_path = os.path.abspath(os.path.expanduser(database_url.database))
    if not os.path.exists(db_path):
        return
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        
        def add_col_if_missing(table, col, col_type):
            try:
                tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                if table in tables:
                    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
                    if col not in cols:
                        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except Exception as err:
                print(f"Migration note for {table}.{col}: {err}")

        # Users table migrations
        add_col_if_missing("users", "full_name", "VARCHAR")
        add_col_if_missing("users", "email", "VARCHAR")
        add_col_if_missing("users", "time_created", "DATETIME")

        # Courses table migrations
        add_col_if_missing("courses", "section", "VARCHAR DEFAULT 'Section A'")
        add_col_if_missing("courses", "join_code", "VARCHAR")
        add_col_if_missing("courses", "color_theme", "VARCHAR DEFAULT 'indigo'")

        # Attendance table migrations
        add_col_if_missing("attendance", "marked_by_id", "INTEGER")
        add_col_if_missing("attendance", "notes", "VARCHAR")
        add_col_if_missing("attendance", "time_created", "DATETIME")
        add_col_if_missing("attendance", "course_id", "INTEGER")

        # Materials table migrations
        add_col_if_missing("class_materials", "file_type", "VARCHAR DEFAULT 'document'")
        add_col_if_missing("class_materials", "course_id", "INTEGER")

        # Assignments table migrations
        add_col_if_missing("assignments", "course_id", "INTEGER")

        # Announcements table migrations
        add_col_if_missing("announcements", "course_id", "INTEGER")

        # Whiteboard lessons table migrations
        add_col_if_missing("whiteboard_lessons", "course_id", "INTEGER")

        # Study groups table migrations
        add_col_if_missing("study_groups", "course_id", "INTEGER")

        # Messages table migrations
        add_col_if_missing("messages", "receiver_id", "INTEGER")
        add_col_if_missing("messages", "is_direct", "BOOLEAN DEFAULT 0")

        # Ensure enrollments table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES users(id),
                FOREIGN KEY (course_id) REFERENCES courses(id)
            )
        """)

        con.commit()
        con.close()
    except Exception as e:
        print(f"Migration helper notice: {e}")