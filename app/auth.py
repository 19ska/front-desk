"""Passwords and sessions. No web framework here, so the rules are easy to read and test.

A session only proves who you are. What you may see comes from allowed_users on
every request, so taking someone off the list removes their access.
"""

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.loader import Role

SESSION_TTL = timedelta(hours=8)
SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


@dataclass(frozen=True)
class CurrentUser:
    email: str
    name: str
    role: Role

    @property
    def can_see_identities(self) -> bool:
        return self.role == "admin"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **SCRYPT)
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def token_hash(token: str) -> str:
    # Only the hash is stored, so a copy of the database can't be used to log in.
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(conn: sqlite3.Connection, email: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    token = secrets.token_urlsafe(32)
    with conn:
        conn.execute(
            "INSERT INTO sessions (token, email, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash(token), email, now.isoformat(), (now + SESSION_TTL).isoformat()),
        )
    return token


def resolve_session(conn: sqlite3.Connection, token: str, now: datetime | None = None) -> CurrentUser | None:
    now = now or datetime.now()
    row = conn.execute(
        """
        SELECT a.email, a.name, a.role
        FROM sessions s
        JOIN users u ON u.email = s.email
        JOIN allowed_users a ON a.email = u.email
        WHERE s.token = ? AND s.expires_at > ?
        """,
        (token_hash(token), now.isoformat()),
    ).fetchone()
    return CurrentUser(row["email"], row["name"], row["role"]) if row else None


def delete_session(conn: sqlite3.Connection, token: str) -> None:
    with conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token_hash(token),))
