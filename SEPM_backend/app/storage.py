import os
from pathlib import Path

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads")).expanduser().resolve()
ASSIGNMENT_UPLOAD_DIR = UPLOAD_DIR / "assignments"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ASSIGNMENT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def public_upload_path(path: Path) -> str:
    return path.relative_to(UPLOAD_DIR.parent).as_posix()
