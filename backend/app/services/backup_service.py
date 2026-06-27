from datetime import datetime
from pathlib import Path
import sqlite3


DATABASE_PATH = Path("data/database/skjoldpatvers.db")
BACKUP_DIR = Path("data/backups")


def create_database_backup() -> Path:
    """
    Creates a consistent SQLite database backup using SQLite's backup API.

    Returns the path to the backup file.
    """

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database finnes ikke: {DATABASE_PATH}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"skjoldpatvers_backup_{timestamp}.db"

    source = sqlite3.connect(str(DATABASE_PATH))
    destination = sqlite3.connect(str(backup_path))

    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    return backup_path


def list_database_backups() -> list[Path]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    return sorted(
        BACKUP_DIR.glob("skjoldpatvers_backup_*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
