# Phase 1: Skeleton + CSV Loader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A FastAPI app that boots, loads both CSVs (cleaned, de-duplicated) into SQLite, and prints a load summary that matches the data audit.

**Architecture:** Pure-Python loader functions (`app/loader.py`) turn raw CSV rows into clean dataclasses with no DB knowledge. `app/db.py` owns the SQLite schema and writes those dataclasses in. `app/main.py` wires both together at startup through a FastAPI lifespan. Visits and the allow-list are reloaded from CSV on every start; user accounts and sessions persist across restarts.

**Tech Stack:** Python 3.13, FastAPI, uvicorn, stdlib `sqlite3` + `csv`, pytest + httpx (TestClient).

**Spec:** `docs/plan.md` (sections 2, 3, 5, 8) and `docs/DATA_NOTES.md`. Read both before starting.

## Global Constraints

- Project root holds only `README.md`, `requirements.txt`, `.gitignore` plus folders (`app/`, `static/`, `tests/`, `docs/`, `data/`, `scripts/`, `var/`). No other root files.
- `data/*.csv` are inputs and are never modified.
- SQLite file lives at `var/frontdesk.db` (gitignored). Tests use `tmp_path` or `:memory:`, never `var/`.
- Email normalisation everywhere = `value.strip().lower()`. One helper, reused.
- Unknown role → that user gets no access (skipped, with a printed warning). Fail closed.
- Duplicate rule (from DATA_NOTES V1): drop a row when an earlier kept row has the same normalised `visitor_email` + `host_email` + sign-in date, signed in ≤ **120 seconds** earlier, **and** the later row has no sign-out.
- Missing days = weekdays (Mon–Fri) between the first and last sign-in date with zero visits. Computed, not hard-coded.
- Timestamps are naive office-local time, format `%Y-%m-%d %H:%M:%S`.
- Run Python via the venv: `.venv/bin/python -m pytest ...` (`-m` puts the project root on `sys.path`).

## Review Focus

1. **Restarting the server must not delete accounts.** Reload visits and allowed users, but keep `users` and `sessions`. Test in Task 3.
2. **A near-duplicate that *has* a sign-out is a real visit.** Keep it. Test in Task 2.
3. **The same visitor returning later the same day (> 120 s) is a real visit.** Keep it. Test in Task 2.
4. **A CSV with a BOM or CRLF line endings loads identically to a clean one.** Test in Task 1.
5. **The same email twice in the allow-list with different roles gets the lower role (viewer).** Test in Task 1.

---

## File Structure

| File | Responsibility |
|---|---|
| `.gitignore` | `.venv/`, `var/`, `__pycache__/`, `.pytest_cache/`, `.DS_Store` |
| `requirements.txt` | `fastapi>=0.115`, `uvicorn>=0.30`, `httpx>=0.27`, `pytest>=8` |
| `app/__init__.py` | empty |
| `app/loader.py` | CSV → dataclasses: `normalise_email`, `AllowedUser`, `load_allowed_users`, `Visit`, `LoadedVisits`, `load_visits` |
| `app/db.py` | `connect`, `init_schema`, `replace_reference_data` |
| `app/main.py` | `create_app(data_dir, db_path)`, module-level `app`, lifespan load + summary, `GET /api/health` |
| `tests/test_loader_users.py`, `tests/test_loader_visits.py`, `tests/test_db.py`, `tests/test_app.py` | tests |
| `README.md` | stub: setup + run commands only (filled in Phase 6) |

---

### Task 1: Project setup + allowed-users loader

**Files:**
- Create: `.gitignore`, `requirements.txt`, `app/__init__.py`, `app/loader.py`
- Test: `tests/test_loader_users.py`

**Interfaces:**
- Produces:
  - `normalise_email(raw: str) -> str`
  - `@dataclass(frozen=True) AllowedUser(email: str, name: str, role: Literal["admin", "viewer"])`
  - `load_allowed_users(path: Path) -> list[AllowedUser]` (sorted by email)

- [ ] **Step 1: Set up the repo and venv**

```bash
cd /Users/devmewada/Desktop/project-001
git init
# write .gitignore and requirements.txt as in File Structure
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
Expected: pip finishes without errors; `git status` shows no `.venv/`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_loader_users.py
from pathlib import Path
from app.loader import normalise_email, load_allowed_users, AllowedUser

REAL = Path("data/allowed_users.csv")

def write(tmp_path, text, name="u.csv", bom=False):
    p = tmp_path / name
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode())
    return p

def test_normalise_email():
    assert normalise_email("  Marcus.Vitale@Brightline.example ") == "marcus.vitale@brightline.example"

def test_real_file_has_3_admins_5_viewers_all_normalised():
    users = load_allowed_users(REAL)
    assert len(users) == 8
    assert sum(u.role == "admin" for u in users) == 3
    assert all(u.email == u.email.strip().lower() for u in users)
    emails = {u.email for u in users}
    assert "marcus.vitale@brightline.example" in emails
    assert "ines.reyes@brightline.example" in emails

def test_crlf_and_bom_load_the_same(tmp_path):
    body = "email,name,role\r\nA@x.example,A,admin\r\n"
    assert load_allowed_users(write(tmp_path, body, bom=True)) == [AllowedUser("a@x.example", "A", "admin")]

def test_unknown_role_is_skipped(tmp_path):
    p = write(tmp_path, "email,name,role\na@x.example,A,editor\nb@x.example,B, Viewer \n")
    assert load_allowed_users(p) == [AllowedUser("b@x.example", "B", "viewer")]

def test_duplicate_email_gets_lower_role(tmp_path):
    p = write(tmp_path, "email,name,role\na@x.example,A,admin\n A@X.example ,A,viewer\n")
    assert load_allowed_users(p) == [AllowedUser("a@x.example", "A", "viewer")]
```

- [ ] **Step 3: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_loader_users.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.loader'`

- [ ] **Step 4: Implement `normalise_email`, `AllowedUser`, `load_allowed_users` in `app/loader.py`**

Open with `encoding="utf-8-sig", newline=""` and `csv.DictReader`. Strip every field. Role `strip().lower()`; anything other than admin/viewer → `print` a warning and skip. On duplicate email keep viewer over admin.

- [ ] **Step 5: Run to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_loader_users.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements.txt app/ tests/test_loader_users.py docs/ scripts/
git commit -m "feat: project setup and allowed-users loader with email normalisation"
```
(`data/` is committed too: the brief ships the CSVs with the repo. Add `data/` to this commit.)

---

### Task 2: Visits loader (parse, derive, de-duplicate, missing days)

**Files:**
- Modify: `app/loader.py`
- Test: `tests/test_loader_visits.py`

**Interfaces:**
- Consumes: `normalise_email` (Task 1)
- Produces:
  - `@dataclass(frozen=True) Visit` with fields: `visit_id: str, visit_date: date, signed_in_at: datetime, signed_out_at: datetime | None, visitor_name: str, visitor_email: str, visitor_company: str, visit_type: str, host_name: str, host_email: str, host_team: str, pre_registered: bool`, plus derived `weekday: int` (0 = Monday), `hour: int`, `duration_min: int | None`
  - `@dataclass(frozen=True) LoadedVisits(visits: list[Visit], dropped_duplicate_ids: list[str], missing_days: list[date])`. `visits` is sorted by `signed_in_at`.
  - `load_visits(path: Path) -> LoadedVisits`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_loader_visits.py
from datetime import date
from pathlib import Path
from app.loader import load_visits

REAL = Path("data/visits.csv")
HEADER = ("visit_id,visit_date,signed_in_at,signed_out_at,visitor_name,visitor_email,visitor_company,"
          "visit_type,host_name,host_email,host_team,pre_registered\n")

def row(vid, t_in, t_out="", email="a@co.example", host="h@b.example"):
    return f"{vid},{t_in[:10]},{t_in},{t_out},A B,{email},Co,guest,H H,{host},Sales,true\n"

def load(tmp_path, *rows):
    p = tmp_path / "v.csv"
    p.write_text(HEADER + "".join(rows))
    return load_visits(p)

def test_real_file_drops_exactly_the_58_duplicates():
    r = load_visits(REAL)
    assert len(r.visits) == 1953
    assert sorted(r.dropped_duplicate_ids) == [f"V{n:06d}" for n in range(1954, 2012)]

def test_real_file_missing_days_are_10_to_13_august():
    assert load_visits(REAL).missing_days == [date(2026, 8, d) for d in (10, 11, 12, 13)]

def test_derived_fields(tmp_path):
    v = load(tmp_path, row("V1", "2026-07-01 09:05:00", "2026-07-01 10:20:00")).visits[0]
    assert (v.weekday, v.hour, v.duration_min, v.pre_registered) == (2, 9, 75, True)

def test_blank_sign_out_is_none(tmp_path):
    assert load(tmp_path, row("V1", "2026-07-01 09:05:00")).visits[0].duration_min is None

def test_double_tap_within_120s_without_sign_out_is_dropped(tmp_path):
    r = load(tmp_path, row("V1", "2026-07-01 09:05:00", "2026-07-01 10:00:00"), row("V2", "2026-07-01 09:06:35"))
    assert r.dropped_duplicate_ids == ["V2"]

def test_near_duplicate_with_sign_out_is_kept(tmp_path):
    r = load(tmp_path, row("V1", "2026-07-01 09:05:00"), row("V2", "2026-07-01 09:05:30", "2026-07-01 10:00:00"))
    assert r.dropped_duplicate_ids == []

def test_same_day_return_visit_is_kept(tmp_path):
    r = load(tmp_path, row("V1", "2026-07-01 09:05:00"), row("V2", "2026-07-01 11:47:00"))
    assert len(r.visits) == 2

def test_different_host_is_not_a_duplicate(tmp_path):
    r = load(tmp_path, row("V1", "2026-07-01 09:05:00"), row("V2", "2026-07-01 09:05:20", host="x@b.example"))
    assert len(r.visits) == 2
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_loader_visits.py -v`
Expected: FAIL with `ImportError: cannot import name 'load_visits'`

- [ ] **Step 3: Implement `Visit`, `LoadedVisits`, `load_visits` in `app/loader.py`**

Read with `utf-8-sig` + `newline=""` and strip every field. Sort rows by `signed_in_at` (not `visit_id`; ids aren't in time order), then de-duplicate in one pass using a dict keyed by `(visitor_email, host_email, date)` → last kept sign-in time, applying the Global Constraints rule. `pre_registered = value.lower() == "true"`. `duration_min = round((out - in).total_seconds() / 60)`. Missing days: every Mon–Fri date from the first to the last visit date that has no kept visit.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: all pass (5 + 8)

- [ ] **Step 5: Commit**

```bash
git add app/loader.py tests/test_loader_visits.py
git commit -m "feat: visits loader with double-tap de-duplication and missing-day detection"
```

---

### Task 3: SQLite schema and data load

**Files:**
- Create: `app/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: `AllowedUser`, `LoadedVisits`, `Visit` (Tasks 1–2)
- Produces:
  - `connect(path: str | Path) -> sqlite3.Connection` (`row_factory = sqlite3.Row`, `check_same_thread=False`, `PRAGMA foreign_keys=ON`). Creates the parent dir if needed.
  - `init_schema(conn) -> None` (idempotent, `CREATE TABLE IF NOT EXISTS`)
  - `replace_reference_data(conn, users: list[AllowedUser], loaded: LoadedVisits) -> None`: in one transaction, empties and refills `allowed_users`, `visits`, `missing_days`. Never touches `users` or `sessions`.
- Schema (later phases depend on these names):
  - `allowed_users(email TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','viewer')))`
  - `users(email TEXT PRIMARY KEY, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)`
  - `sessions(token TEXT PRIMARY KEY, email TEXT NOT NULL REFERENCES users(email), created_at TEXT NOT NULL, expires_at TEXT NOT NULL)`
  - `visits(visit_id TEXT PRIMARY KEY, visit_date TEXT, signed_in_at TEXT, signed_out_at TEXT NULL, visitor_name, visitor_email, visitor_company, visit_type, host_name, host_email, host_team TEXT, pre_registered INTEGER, weekday INTEGER, hour INTEGER, duration_min INTEGER NULL)`. Dates stored ISO (`YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS`). Indexes on `visit_date` and `visit_type`.
  - `missing_days(day TEXT PRIMARY KEY)`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_db.py
from pathlib import Path
from app import db
from app.loader import load_allowed_users, load_visits

def loaded_conn():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    db.replace_reference_data(conn, load_allowed_users(Path("data/allowed_users.csv")),
                              load_visits(Path("data/visits.csv")))
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
    db.replace_reference_data(conn, load_allowed_users(Path("data/allowed_users.csv")), load_visits(Path("data/visits.csv")))
    assert count(conn, "users") == 1 and count(conn, "visits") == 1953

def test_init_schema_is_idempotent():
    conn = loaded_conn()
    db.init_schema(conn)
    assert count(conn, "visits") == 1953
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_db.py -v`
Expected: FAIL with `ImportError: cannot import name 'db'`

- [ ] **Step 3: Implement `connect`, `init_schema`, `replace_reference_data` in `app/db.py`**

Use `executemany` for inserts; wrap the delete+insert in `with conn:` so a failed load leaves the old data intact.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat: SQLite schema and reference-data load that preserves accounts"
```

---

### Task 4: App boot, load summary, health check, README stub

**Files:**
- Create: `app/main.py`, `README.md`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `connect`, `init_schema`, `replace_reference_data` (Task 3); `load_allowed_users`, `load_visits` (Tasks 1–2)
- Produces:
  - `create_app(data_dir: Path = Path("data"), db_path: Path = Path("var/frontdesk.db")) -> FastAPI`. Later phases add routers to this.
  - The connection is stored on `app.state.db`. Later phases read it from `request.app.state.db`.
  - Module-level `app = create_app()` so `uvicorn app.main:app` works.
  - `GET /api/health` → `200 {"status": "ok"}` (no data, no auth).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_app.py
from fastapi.testclient import TestClient
from app.main import create_app

def test_boots_loads_and_reports_health(tmp_path, capsys):
    app = create_app(db_path=tmp_path / "t.db")
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        assert app.state.db.execute("SELECT COUNT(*) FROM visits").fetchone()[0] == 1953
    out = capsys.readouterr().out
    assert "1953 visits" in out and "58 duplicate" in out and "2026-08-10" in out
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Implement `create_app` in `app/main.py`**

FastAPI `lifespan` context manager: connect → init_schema → load both CSVs → `replace_reference_data` → print the summary below → yield → close.

Exact summary copy:
```
Loaded 8 allowed users (3 admin, 5 viewer)
Loaded 1953 visits from 2026-07-01 to 2026-09-30 (dropped 58 duplicate sign-ins)
No sign-ins recorded on: 2026-08-10, 2026-08-11, 2026-08-12, 2026-08-13
```
(numbers come from the data, not hard-coded).

- [ ] **Step 4: Write `README.md` stub**

Sections: title, one-line description, **Setup** (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`), **Run** (`.venv/bin/uvicorn app.main:app --reload`, then open http://127.0.0.1:8000), **Test** (`.venv/bin/python -m pytest`). Phase 6 fills in the rest.

- [ ] **Step 5: Run everything and boot for real**

Run: `.venv/bin/python -m pytest -v` → all pass.
Run: `.venv/bin/uvicorn app.main:app` (background), then `curl -s localhost:8000/api/health` → `{"status":"ok"}`, and the server log shows the three summary lines. Stop the server. Check `ls` at the root shows only allowed files/folders.

- [ ] **Step 6: Commit**

```bash
git add app/main.py README.md tests/test_app.py
git commit -m "feat: FastAPI app boots, loads CSVs into SQLite, prints load summary"
```

---

## Phase 1 done when
- `.venv/bin/python -m pytest` passes (18 tests).
- `uvicorn app.main:app` prints the three summary lines with 8 / 3 / 5 / 1953 / 58 / 10–13 Aug.
- Restarting the server keeps `users` rows.
- Root contains only `README.md`, `requirements.txt`, `.gitignore` and folders.
