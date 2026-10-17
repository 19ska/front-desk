from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app import auth, db
from app.loader import load_allowed_users, load_visits

DANA = "dana.whitfield@brightline.example"
NOW = datetime(2026, 10, 16, 9, 0, 0)


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_schema(c)
    db.replace_reference_data(c, load_allowed_users(Path("data/allowed_users.csv")), load_visits(Path("data/visits.csv")))
    c.execute("INSERT INTO users VALUES (?, ?, ?)", (DANA, auth.hash_password("correct horse"), NOW.isoformat()))
    c.commit()
    return c


def test_hash_round_trip_and_salted():
    h = auth.hash_password("correct horse")
    assert h.startswith("scrypt$") and h != auth.hash_password("correct horse")
    assert auth.verify_password("correct horse", h) and not auth.verify_password("wrong", h)


def test_verify_malformed_hash_is_false():
    assert auth.verify_password("x", "garbage") is False


def test_session_resolves_to_user_with_role_from_allow_list(conn):
    token = auth.create_session(conn, DANA, now=NOW)
    assert auth.resolve_session(conn, token, now=NOW) == auth.CurrentUser(DANA, "Dana Whitfield", "admin")


def test_token_is_not_stored_in_plain_text(conn):
    token = auth.create_session(conn, DANA, now=NOW)
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE token = ?", (token,)).fetchone()[0] == 0


def test_expired_session_is_rejected(conn):
    token = auth.create_session(conn, DANA, now=NOW)
    assert auth.resolve_session(conn, token, now=NOW + auth.SESSION_TTL + timedelta(seconds=1)) is None


def test_unknown_token_is_rejected(conn):
    assert auth.resolve_session(conn, "nope", now=NOW) is None


def test_removed_from_allow_list_is_rejected(conn):
    token = auth.create_session(conn, DANA, now=NOW)
    conn.execute("DELETE FROM allowed_users WHERE email = ?", (DANA,))
    assert auth.resolve_session(conn, token, now=NOW) is None


def test_deleted_session_is_rejected(conn):
    token = auth.create_session(conn, DANA, now=NOW)
    auth.delete_session(conn, token)
    assert auth.resolve_session(conn, token, now=NOW) is None
