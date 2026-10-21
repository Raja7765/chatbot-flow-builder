"""
Database configuration and management module for the Chatbot Flow Builder.
This module uses Python's built-in sqlite3 module to manage database connections,
ensure safe connection cleanup, initialize the database directory, and create tables.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Generator, Optional, Union

# Define paths relative to this file to ensure predictability across working directories:
# __file__ -> backend/app/database.py
# .parent -> backend/app
# .parent.parent -> backend
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "flows.db"


def get_utc_now_iso() -> str:
    """
    Return the current UTC timestamp formatted as an ISO 8601 string.
    Example: '2026-10-21T06:07:35.123456+00:00'
    """
    return datetime.now(timezone.utc).isoformat()


def ensure_db_directory(db_path: Union[Path, str]) -> Path:
    """
    Ensure the parent directory for the database file exists.
    Creates parent directories if they do not exist.

    Args:
        db_path: The file path to the SQLite database.

    Returns:
        Path: The resolved absolute Path object.
    """
    resolved_path = Path(db_path).resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return resolved_path


@contextmanager
def get_db_connection(
    db_path: Optional[Union[Path, str]] = None
) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager providing a safely managed SQLite database connection.
    Automatically commits on success, rolls back on error, and ensures the
    connection is closed in all cases (including exceptions).

    Args:
        db_path: Optional path to the SQLite database file. Defaults to DEFAULT_DB_PATH.

    Yields:
        sqlite3.Connection: An open SQLite connection with Row factory enabled.
    """
    target_path = ensure_db_directory(db_path or DEFAULT_DB_PATH)
    conn = sqlite3.connect(target_path)
    # Enable dict-like column access by column name (e.g. row['name'])
    conn.row_factory = sqlite3.Row
    # Enable foreign keys support in SQLite
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Union[Path, str]] = None) -> None:
    """
    Initialize the SQLite database by creating the required tables if they don't exist.

    Table 'flows':
    - id: TEXT PRIMARY KEY (unique identifier for each flow)
    - name: TEXT NOT NULL (display name of the chatbot flow)
    - description: TEXT (optional description of the flow's purpose)
    - flow_data: TEXT NOT NULL (JSON-serialized flow configuration: nodes, edges, etc.)
    - created_at: TEXT NOT NULL (ISO 8601 UTC creation timestamp)
    - updated_at: TEXT NOT NULL (ISO 8601 UTC last update timestamp)

    Args:
        db_path: Optional path to the database file. If omitted, uses DEFAULT_DB_PATH.
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS flows (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        flow_data TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """
    with get_db_connection(db_path) as conn:
        conn.execute(create_table_sql)


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency that yields a managed SQLite database connection.
    Automatically commits upon request completion, rolls back on errors,
    and safely closes the connection in all scenarios.
    """
    with get_db_connection() as conn:
        yield conn

