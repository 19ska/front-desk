from pathlib import Path

from app import db
from app.loader import load_allowed_users, load_visits


def reference_data():
    return load_allowed_users(Path("data/allowed_users.csv")), load_visits(Path("data/visits.csv"))


def loaded_conn():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    db.replace_reference_data(conn, *reference_data())
    return conn


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_counts_after_load():
    conn = loaded_conn()
    assert (count(conn, "allowed_users"), count(conn, "visits"), count(conn, "missing_days")) == (8, 1953, 4)


def test_visit_row_round_trips():
    r = loaded_conn().execute("SELECT * FROM visits WHERE visit_id='V001912'").fetchone()
    assert (r["signed_in_at"], r["signed_out_at"], r["duration_min"]) == ("2026-09-30 15:27:00", "2026-09-30 16:38:00", 71)


def test_reload_keeps_accounts():
    conn = loaded_conn()
    conn.execute("INSERT INTO users VALUES ('dana.whitfield@brightline.example','x','2026-10-16')")
    conn.commit()
    db.replace_reference_data(conn, *reference_data())
    assert count(conn, "users") == 1 and count(conn, "visits") == 1953


def test_init_schema_is_idempotent():
    conn = loaded_conn()
    db.init_schema(conn)
    assert count(conn, "visits") == 1953
