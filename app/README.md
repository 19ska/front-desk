# app/: the API

FastAPI + SQLite. Everything that decides **who sees what** lives here, not in the pages.

## Where the rules live

| Rule | Where |
|---|---|
| A viewer's query never reads identity columns | `visits.py`: `VIEWER_COLUMNS` / `ADMIN_COLUMNS` (lines 17–19), used by `columns_sql`, `list_visits`, `get_visit` |
| Role is read from the access list on every request | `auth.py`: `resolve_session` (line 64) joins sessions → users → `allowed_users` |
| No session → 401; viewer on admin → 403 | `deps.py`: `current_user` (line 33), `require_admin` (line 41) |
| Only known query parameters; values bound, never formatted into SQL | `filters.py`: `parse_filters` (line 56), `filters_sql` (line 90) |
| Every error is `{"error": "…"}`; 500s never show details | `errors.py`: `install_error_handlers` |
| Emails match ignoring case and spaces | `loader.py`: `normalise_email` |

## Request flow

```
request → routes/*.py → deps.current_user (cookie or Bearer → auth.resolve_session → role) → filters.parse_filters
        → visits.list_visits / get_visit / compute_stats (SELECT the role's columns only) → JSON
```

## Files

| File | Does |
|---|---|
| `main.py` | `create_app()`: loads the CSVs at start-up, wires routers, error handlers and pages |
| `loader.py` | Reads both CSVs: normalises emails, drops double-tap duplicates, finds days with no data. No DB code |
| `db.py` | SQLite schema; reloads visits and the access list on start, keeps accounts and sessions |
| `auth.py` | Password hashing (scrypt), sessions (hashed tokens, 8 h), `resolve_session` |
| `deps.py` | FastAPI dependencies: per-request DB connection, `current_user`, `require_admin` |
| `filters.py` | Validates `from`/`to`/`type`/`page`/`page_size` into a 400 or a SQL `WHERE` |
| `visits.py` | The visit list, one visit, and the stats, all by role |
| `errors.py` | JSON errors for every failure |
| `pages.py` | Serves the page shell for page URLs (404 for unknown), `/static`, `/` → `/visits` |
| `routes/auth.py`, `routes/visits.py`, `routes/admin.py` | The endpoints (thin) |

The spec is in [../docs/API.md](../docs/API.md). The data rules and why they exist are in [../docs/DATA_NOTES.md](../docs/DATA_NOTES.md).
