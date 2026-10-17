# tests/

```bash
.venv/bin/python -m pytest              # Python: API, loader, auth, leak sweep
node --test 'tests/js/*.test.mjs'       # JavaScript: page logic (Node 22+)
```

| File | Covers |
|---|---|
| `test_loader_users.py`, `test_loader_visits.py` | CSV cleaning: email normalisation, unknown roles, the 58 duplicates, missing days, malformed files |
| `test_db.py`, `test_app.py` | Schema, reload keeps accounts, start-up summary |
| `test_errors.py` | Every error is JSON; validation → 400; crashes → a safe 500 |
| `test_auth_core.py`, `test_auth_api.py` | Hashing, sessions, expiry, sign-up rules, login, logout, cookie flags, removed-from-list → 401 |
| `test_filters.py`, `test_visits_api.py`, `test_stats_api.py`, `test_admin_api.py` | Filters and their 400s, role-projected visits, stats, admin list |
| **`test_leak.py`** | **The reviewers' check, automated:** as viewer, sweep every data endpoint and search for every name, email and company in the CSV. An admin control proves the sweep can find them |
| `test_pages.py`, `test_docs.py` | Page URLs serve the shell (404 for unknown); every API route is in `docs/API.md`; README logins match the script |
| `js/*.test.mjs` | Routes, URL state, safe redirects, formatting, headline, and `h()` never creating markup |

Notes:
- `conftest.py` gives each test a fresh database (`client` fixture), plus `as_user(client, email)`, which signs up, logs in and returns Bearer headers.
- `extra_route()` registers test-only endpoints ahead of the page catch-all.
- The tests use the real `data/*.csv`, so some assert this export's numbers (1,953 visits, Tuesday and Wednesday busiest). The rules themselves are also tested on small hand-made files.
