from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from .settings import Settings


SCHEMA_VERSION = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    suffix TEXT,
    size_bytes INTEGER,
    mtime REAL,
    category TEXT,
    summary TEXT,
    sensitive INTEGER DEFAULT 0,
    indexed_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target TEXT,
    dry_run INTEGER DEFAULT 1,
    status TEXT,
    details TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    source TEXT,
    tags TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    details TEXT
);
CREATE TABLE IF NOT EXISTS research_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    title TEXT,
    summary TEXT,
    note_path TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT,
    body TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_kind_time ON events(kind, occurred_at DESC);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def initialize_database(path: Path) -> None:
    _initialize_database(path)


def _initialize_database(path: Path) -> None:
    """Internal implementation kept separate so schema setup stays easy to test."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
        connection.execute(
            "INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,?)",
            ("schema_version", str(SCHEMA_VERSION), utc_now()),
        )


def migrate_legacy_database(settings: Settings) -> tuple[Path, bool]:
    """Move the legacy database to XDG storage and leave a compatibility symlink."""
    target = settings.database_path
    if target.exists():
        _initialize_database(target)
        return target, False
    legacy = settings.root / "data" / "db" / "agent_os.sqlite"
    target.parent.mkdir(parents=True, exist_ok=True)
    if legacy.is_file():
        legacy.replace(target)
        legacy.symlink_to(target)
        migrated = True
    else:
        migrated = False
    _initialize_database(target)
    return target, migrated


@contextmanager
def connect(settings: Settings) -> Iterator[sqlite3.Connection]:
    _initialize_database(settings.database_path)
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def log_event(
    settings: Settings,
    kind: str,
    title: str = "",
    body: str = "",
    metadata: dict[str, object] | None = None,
) -> None:
    with connect(settings) as connection:
        connection.execute(
            "INSERT INTO events(occurred_at,kind,title,body,metadata_json) VALUES(?,?,?,?,?)",
            (utc_now(), kind, title, body, json.dumps(metadata or {}, sort_keys=True)),
        )
