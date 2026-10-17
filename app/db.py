"""SQLite schema and loading.

Visits and the allow-list come from the CSVs and are replaced on every start.
User accounts and sessions are created by the app and survive restarts.
"""

import sqlite3
from pathlib import Path

from app.loader import TIMESTAMP, AllowedUser, LoadedVisits

SCHEMA = """
CREATE TABLE IF NOT EXISTS allowed_users (
    email TEXT PRIMARY KEY,
    name  TEXT NOT NULL,
    role  TEXT NOT NULL CHECK (role IN ('admin', 'viewer'))
);
CREATE TABLE IF NOT EXISTS users (
    email         TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    email      TEXT NOT NULL REFERENCES users (email),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS visits (
    visit_id        TEXT PRIMARY KEY,
    visit_date      TEXT NOT NULL,
    signed_in_at    TEXT NOT NULL,
    signed_out_at   TEXT,
    visitor_name    TEXT NOT NULL,
    visitor_email   TEXT NOT NULL,
    visitor_company TEXT NOT NULL,
    visit_type      TEXT NOT NULL,
    host_name       TEXT NOT NULL,
    host_email      TEXT NOT NULL,
    host_team       TEXT NOT NULL,
    pre_registered  INTEGER NOT NULL,
    weekday         INTEGER NOT NULL,
    hour            INTEGER NOT NULL,
    duration_min    INTEGER
);
CREATE INDEX IF NOT EXISTS visits_by_date ON visits (visit_date);
CREATE INDEX IF NOT EXISTS visits_by_type ON visits (visit_type);
CREATE TABLE IF NOT EXISTS missing_days (
    day TEXT PRIMARY KEY
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def replace_reference_data(conn: sqlite3.Connection, users: list[AllowedUser], loaded: LoadedVisits) -> None:
    # One transaction: a failed load leaves the previous data in place.
    with conn:
        conn.execute("DELETE FROM allowed_users")
        conn.execute("DELETE FROM visits")
        conn.execute("DELETE FROM missing_days")
        conn.executemany("INSERT INTO allowed_users VALUES (?, ?, ?)", [(u.email, u.name, u.role) for u in users])
        conn.executemany(
            "INSERT INTO visits VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    v.visit_id,
                    v.visit_date.isoformat(),
                    v.signed_in_at.strftime(TIMESTAMP),
                    v.signed_out_at.strftime(TIMESTAMP) if v.signed_out_at else None,
                    v.visitor_name,
                    v.visitor_email,
                    v.visitor_company,
                    v.visit_type,
                    v.host_name,
                    v.host_email,
                    v.host_team,
                    int(v.pre_registered),
                    v.weekday,
                    v.hour,
                    v.duration_min,
                )
                for v in loaded.visits
            ],
        )
        conn.executemany("INSERT INTO missing_days VALUES (?)", [(d.isoformat(),) for d in loaded.missing_days])
