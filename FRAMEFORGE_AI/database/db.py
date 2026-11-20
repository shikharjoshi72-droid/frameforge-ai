"""SQLite connection helpers."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config.settings import DB_PATH
from database.models import SCHEMA


class DatabaseError(Exception):
    """Raised for any database failure, with a user-presentable message."""


def connect(path=None) -> sqlite3.Connection:
    path = Path(path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session(path=None):
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise DatabaseError(f"Database error: {exc}") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path=None) -> None:
    with session(path) as conn:
        conn.executescript(SCHEMA)
