# Phase 3: Role-Aware Data Endpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The visit list, single visit, stats and admin-users endpoints. Filtering, paging and counting all happen on the server. A viewer's response never contains a visitor's or host's name, email or company, anywhere.

**Architecture:** `app/filters.py` turns query parameters into a validated `VisitFilters` (or a 400) and a SQL `WHERE` fragment. `app/visits.py` holds the queries with no FastAPI in it. **Role projection happens in the SELECT itself**: a viewer query never reads identity columns from the database. Admin-only fields are added by a separate column list, never deleted afterwards. `app/routes/visits.py` and `app/routes/admin.py` are thin HTTP wrappers. An automated leak test does the reviewers' check: sign in as a viewer, call every data endpoint, and search the raw bytes for every name and email in the CSV.

**Tech Stack:** FastAPI, SQLite, stdlib `statistics.median`. No new dependencies.

**Spec:** `docs/plan.md` sections 2 (API rules), 5 (projection table, leak routes), 6 (API table), 8 (leak test). `docs/DATA_NOTES.md` findings V2–V5 (gap, sign-outs, per-day averages, hours).

## Global Constraints

- **Nothing data-specific in `app/`.** Visit types, teams, the date range, the hours shown and the missing days all come from the loaded data. (User requirement: it must work for any export.)
- Viewer visit fields: `visit_id, date, signed_in, signed_out, duration_min, visit_type, host_team, pre_registered`. Admin gets those plus `visitor: {name, email, company}` and `host: {name, email}`. Viewer JSON has **no `visitor` or `host` key at all**.
- Column lists are module constants. User input never becomes part of SQL text; values are bound as `?` parameters.
- Filters (query string): `from`, `to` (inclusive dates, `YYYY-MM-DD`), `type`. The list endpoint also takes `page` (default 1) and `page_size` (default 50, max 200). **Any other query parameter → 400** `Unknown filter: <name>. Use from, to, type[, page, page_size].` Repeating a parameter → 400 `Give <name> only once.`
- Exact 400 messages:
  - bad date: `<from|to> must be a date written as YYYY-MM-DD.`
  - end before start: `The end date (<to>) is before the start date (<from>).`
  - unknown type: `Unknown visit type '<value, max 40 chars>'. Choose one of: <sorted types from data, comma-separated>.`
  - bad page/page_size: `<name> must be a whole number from 1 to <max>.` (page has no max: `page must be a whole number from 1.`)
  - page past the end (only when total > 0): `Page <n> doesn't exist. There are <total_pages> pages.`
- Type matching is case-insensitive and trims spaces (`?type= Interview ` works).
- Unknown visit id → 404 `No visit with id <id>.` (any id string; no id format is assumed). This includes the 58 de-duplicated ids.
- The list is ordered newest first: `signed_in_at DESC, visit_id DESC`.
- Stats definitions:
  - **operating days** = distinct dates in the range that have at least one visit of any type. This is the denominator. It's computed from the data, so the 10–13 Aug gap and weekends drop out on their own, while a day with no vendors but other visitors still counts as a real zero for vendors.
  - `by_weekday`: one entry per weekday that has ≥1 operating day, in Mon→Sun order: `{weekday: 0-6, name: "Monday"…, visits, operating_days, avg_per_day (1 dp)}`.
  - `by_hour`: every hour from the earliest to the latest sign-in hour **in the whole dataset** (so empty hours like 12 show as 0): `{hour, visits}`.
  - **busiest** = every entry whose value is ≥ 95% of the top value (ties are reported, not hidden). `busiest_days: [names]` by `avg_per_day`; `busiest_hours: [ints]` by `visits`. Empty lists when there are no visits.
  - `visit_length: {median_min: int | null (round(median)), measured_visits: int, total_visits: int}`. Only visits with a sign-out are measured.
  - `range: {from, to}` = the requested range clipped to the data's first/last date (null filters → data bounds). `missing_days: [ISO dates]` = the loader's missing days inside the range.
- `/api/admin/users` → `{"users": [{email, name, role, signed_up: bool}]}` ordered admins first, then by name. 403 for viewers (via `require_admin`).

## Review Focus

1. **A viewer adds identity-shaped parameters** (`?visitor_name=…`, `?q=…`, `?sort=visitor_name`). They must get a 400, not a silently filtered or reordered result. Test in Task 1.
2. **A filter that matches nothing** (a date range with no visits, or the 10–13 Aug gap) must return 200 with empty items, total 0 and stats with empty busiest lists and a null median, not a 400 or 500. Test in Tasks 2 and 3.
3. **A range entirely outside the data** (e.g. 2030) must return empty results, not an error. Test in Task 3.
4. **Asking for page 999** must get a 400 saying how many pages exist. Test in Task 2.
5. **A viewer asks for a dropped duplicate id or a made-up id** and gets the same 404 an admin gets, so the response reveals nothing. Test in Task 2.

---

## File Structure

| File | Responsibility |
|---|---|
| `app/filters.py` | `VisitFilters`, `parse_filters`, `parse_page`, `filters_sql`, `visit_types` |
| `app/visits.py` | `VIEWER_COLUMNS`, `ADMIN_COLUMNS`, `list_visits`, `get_visit`, `compute_stats` |
| `app/routes/visits.py` | `GET /api/visit-types`, `GET /api/visits`, `GET /api/visits/{visit_id}`, `GET /api/stats` |
| `app/routes/admin.py` | `GET /api/admin/users` |
| `app/main.py` (modify) | include both routers |
| `tests/conftest.py` (modify) | `as_user(client, email) -> dict` (sign up, log in, **clear the client's cookies**, return Bearer headers) |
| `tests/test_filters.py`, `tests/test_visits_api.py`, `tests/test_stats_api.py`, `tests/test_admin_api.py`, `tests/test_leak.py` | tests |

`as_user` must clear cookies because a stale cookie currently wins over a Bearer header (a deferred minor from Phase 2). Without this, a test meant to act as Dana could silently act as Sam.

---

### Task 1: Filter parsing + `GET /api/visit-types`

**Files:**
- Create: `app/filters.py`, `app/routes/visits.py` (visit-types only), `tests/test_filters.py`
- Modify: `app/main.py`, `tests/conftest.py`

**Interfaces:**
- Consumes: `get_conn`, `current_user` (Phase 2)
- Produces:
  - `@dataclass(frozen=True) VisitFilters(date_from: date | None, date_to: date | None, visit_type: str | None)`
  - `visit_types(conn) -> list[str]` (distinct, sorted)
  - `parse_filters(params: QueryParams, conn, extra: frozenset[str] = frozenset()) -> VisitFilters`. Raises `HTTPException(400, …)`. `extra` names the other parameters the caller accepts (e.g. `{"page", "page_size"}`); anything else → `Unknown filter`.
  - `parse_page(params: QueryParams) -> tuple[int, int]` → `(page, page_size)`
  - `filters_sql(f: VisitFilters) -> tuple[str, list]` → (`"WHERE …"` or `""`, params). Filters on `visit_date` (inclusive both ends) and `visit_type`.
  - `GET /api/visit-types` → `{"visit_types": [...]}` (signed in, either role)
  - conftest `as_user(client, email: str) -> dict[str, str]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_filters.py
import pytest
from fastapi.testclient import TestClient

from tests.conftest import as_user

SAM = "sam.ferreira@brightline.example"


@pytest.fixture
def viewer(client):
    return as_user(client, SAM)


def err(client, headers, query):
    r = client.get(f"/api/visits{query}", headers=headers)
    return r.status_code, r.json().get("error")


def test_visit_types_come_from_the_data(client, viewer):
    assert client.get("/api/visit-types", headers=viewer).json() == {"visit_types": ["contractor", "guest", "interview", "vendor"]}


def test_visit_types_needs_a_session(client):
    assert client.get("/api/visit-types").status_code == 401


def test_bad_dates(client, viewer):
    assert err(client, viewer, "?from=14/08/2026") == (400, "from must be a date written as YYYY-MM-DD.")
    assert err(client, viewer, "?to=2026-02-30") == (400, "to must be a date written as YYYY-MM-DD.")
    assert err(client, viewer, "?from=2026-08-31&to=2026-08-01") == (400, "The end date (2026-08-01) is before the start date (2026-08-31).")


def test_unknown_type_lists_the_real_ones(client, viewer):
    assert err(client, viewer, "?type=intervew") == (400, "Unknown visit type 'intervew'. Choose one of: contractor, guest, interview, vendor.")


def test_identity_shaped_params_are_refused(client, viewer):
    for q in ("?visitor_name=Felix", "?q=Felix", "?sort=visitor_name", "?visitor_email=x"):
        status, message = err(client, viewer, q)
        assert status == 400 and message.startswith("Unknown filter:"), q


def test_repeated_param_is_refused(client, viewer):
    assert err(client, viewer, "?type=guest&type=vendor") == (400, "Give type only once.")


def test_bad_paging(client, viewer):
    assert err(client, viewer, "?page=0") == (400, "page must be a whole number from 1.")
    assert err(client, viewer, "?page_size=500") == (400, "page_size must be a whole number from 1 to 200.")
    assert err(client, viewer, "?page=two") == (400, "page must be a whole number from 1.")
```

(These hit `/api/visits`, which Task 2 implements. In this task, give `/api/visits` a stub that calls `parse_filters` + `parse_page` and returns `{}`, so the validation tests can pass. Task 2 replaces the body.)

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_filters.py -q`
Expected: FAIL with `ImportError: cannot import name 'as_user'`, then 404s.

- [ ] **Step 3: Implement** `app/filters.py`, the routes, `as_user`, and include the router in `create_app`. Read parameters with `params.getlist(name)` so repeats are caught. Validate dates with `date.fromisoformat` **and** a `^\d{4}-\d{2}-\d{2}$` check (fromisoformat also accepts other shapes).

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass

- [ ] **Step 5: Commit** `feat: validated visit filters and /api/visit-types`

---

### Task 2: Visit list and single visit, projected by role + the leak test

**Files:**
- Create: `app/visits.py` (`list_visits`, `get_visit`, column lists), `tests/test_visits_api.py`, `tests/test_leak.py`
- Modify: `app/routes/visits.py`

**Interfaces:**
- Consumes: `VisitFilters`, `parse_filters`, `parse_page`, `filters_sql` (Task 1); `CurrentUser.can_see_identities` (Phase 2)
- Produces:
  - `list_visits(conn, f: VisitFilters, page: int, page_size: int, identities: bool) -> dict` → `{"items": [...], "page", "page_size", "total", "total_pages"}` (`total_pages` is 0 when `total` is 0)
  - `get_visit(conn, visit_id: str, identities: bool) -> dict | None`
  - `GET /api/visits` → that dict plus `"filters": {"from", "to", "type"}` (echoing the parsed values, nulls when absent)
  - `GET /api/visits/{visit_id}` → one item, or 404
  - `tests/test_leak.py` defines `VIEWER_ENDPOINTS: list[str]`, which Tasks 3–4 extend

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_visits_api.py
import pytest

from tests.conftest import as_user

SAM, DANA = "sam.ferreira@brightline.example", "dana.whitfield@brightline.example"
VIEWER_KEYS = {"visit_id", "date", "signed_in", "signed_out", "duration_min", "visit_type", "host_team", "pre_registered"}


@pytest.fixture
def viewer(client):
    return as_user(client, SAM)


@pytest.fixture
def admin(client):
    return as_user(client, DANA)


def test_list_is_paged_newest_first(client, viewer):
    body = client.get("/api/visits", headers=viewer).json()
    assert (body["total"], body["page"], body["page_size"], body["total_pages"]) == (1953, 1, 50, 40)
    assert len(body["items"]) == 50
    assert body["items"][0]["signed_in"] >= body["items"][-1]["signed_in"]
    assert body["filters"] == {"from": None, "to": None, "type": None}


def test_viewer_items_have_exactly_the_viewer_fields(client, viewer):
    item = client.get("/api/visits", headers=viewer).json()["items"][0]
    assert set(item) == VIEWER_KEYS


def test_admin_items_add_visitor_and_host(client, admin):
    item = client.get("/api/visits/V001912", headers=admin).json()
    assert item["visitor"] == {"name": "Sofia Reyes", "email": "sreyes@oakfieldlega.example", "company": "Oakfield Legal"}
    assert item["host"] == {"name": "Nadia Ferreira", "email": "nadia.ferreira@brightline.example"}
    assert set(item) == VIEWER_KEYS | {"visitor", "host"}


def test_filters_are_inclusive_and_case_insensitive(client, viewer):
    body = client.get("/api/visits?from=2026-08-01&to=2026-08-31&type= Interview ", headers=viewer).json()
    assert body["total"] == 115
    assert body["filters"] == {"from": "2026-08-01", "to": "2026-08-31", "type": "interview"}
    assert client.get("/api/visits?from=2026-09-30&to=2026-09-30", headers=viewer).json()["total"] == 46


def test_gap_days_return_an_honest_empty_200(client, viewer):
    body = client.get("/api/visits?from=2026-08-10&to=2026-08-13", headers=viewer).json()
    assert (body["total"], body["items"], body["total_pages"]) == (0, [], 0)


def test_page_past_the_end(client, viewer):
    r = client.get("/api/visits?page=999", headers=viewer)
    assert r.status_code == 400 and r.json() == {"error": "Page 999 doesn't exist. There are 40 pages."}


def test_single_visit_viewer_has_no_identity(client, viewer):
    item = client.get("/api/visits/V001912", headers=viewer).json()
    assert set(item) == VIEWER_KEYS and item["duration_min"] == 71


def test_unknown_and_deduplicated_ids_are_404_for_both_roles(client, viewer, admin):
    for headers in (viewer, admin):
        for vid in ("V001996", "nope"):
            r = client.get(f"/api/visits/{vid}", headers=headers)
            assert r.status_code == 404 and r.json() == {"error": f"No visit with id {vid}."}


def test_visits_need_a_session(client):
    assert client.get("/api/visits").status_code == 401
    assert client.get("/api/visits/V001912").status_code == 401
```

```python
# tests/test_leak.py
"""The reviewers' test, automated: sign in as a viewer and search every data response for identities."""
import csv

import pytest

from tests.conftest import as_user

SAM, DANA = "sam.ferreira@brightline.example", "dana.whitfield@brightline.example"


def identities():
    with open("data/visits.csv", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    cols = ("visitor_name", "visitor_email", "visitor_company", "host_name", "host_email")
    return sorted({r[c].strip().lower() for r in rows for c in cols})


def all_list_pages():
    return [f"/api/visits?page={p}&page_size=200" for p in range(1, 11)]


def sample_ids():
    with open("data/visits.csv", newline="", encoding="utf-8-sig") as f:
        return [r["visit_id"] for r in csv.DictReader(f)][::25]


VIEWER_ENDPOINTS = (
    all_list_pages()
    + [f"/api/visits?type={t}" for t in ("guest", "interview", "contractor", "vendor")]
    + ["/api/visits?from=2026-08-01&to=2026-08-31", "/api/visit-types"]
    + [f"/api/visits/{i}" for i in sample_ids()]
)


def fetch_all(client, headers, endpoints):
    bodies = []
    for url in endpoints:
        r = client.get(url, headers=headers)
        assert r.status_code in (200, 404), (url, r.status_code)
        bodies.append(r.text.lower())
    return bodies


def test_viewer_responses_contain_no_name_email_or_company(client):
    viewer = as_user(client, SAM)
    blob = "\n".join(fetch_all(client, viewer, VIEWER_ENDPOINTS))
    leaked = [needle for needle in identities() if needle in blob]
    assert leaked == []
    for key in ('"visitor"', '"host"', "visitor_name", "visitor_email", "host_name", "host_email", "company"):
        assert key not in blob, key


def test_the_same_sweep_as_admin_does_find_names(client):
    # Proves the sweep can see a leak: the admin's responses must contain identities.
    admin = as_user(client, DANA)
    blob = "\n".join(fetch_all(client, admin, VIEWER_ENDPOINTS[:1]))
    assert sum(needle in blob for needle in identities()) > 50
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_visits_api.py tests/test_leak.py -q`
Expected: FAIL (`/api/visits` returns the Task 1 stub `{}`, so `KeyError: 'total'`; `/api/visits/{id}` is a 404 for every id)

- [ ] **Step 3: Implement**

`app/visits.py`:
```python
VIEWER_COLUMNS = ("visit_id", "visit_date", "signed_in_at", "signed_out_at", "duration_min",
                  "visit_type", "host_team", "pre_registered")
ADMIN_COLUMNS = VIEWER_COLUMNS + ("visitor_name", "visitor_email", "visitor_company", "host_name", "host_email")
```
`row_to_item(row, identities)` maps to the JSON field names in Global Constraints (`pre_registered` → bool), adding `visitor`/`host` only when `identities`. SELECT `ADMIN_COLUMNS` only when `identities` is True. Routes pass `user.can_see_identities`.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass

- [ ] **Step 5: Commit** `feat: role-projected visit list and detail, with an automated viewer leak test`

---

### Task 3: `GET /api/stats`

**Files:**
- Create: `tests/test_stats_api.py`
- Modify: `app/visits.py` (add `compute_stats`), `app/routes/visits.py`, `tests/test_leak.py` (extend `VIEWER_ENDPOINTS` with `"/api/stats"`, `"/api/stats?type=interview"`, `"/api/stats?from=2026-08-01&to=2026-08-31"`)

**Interfaces:**
- Consumes: `VisitFilters`, `filters_sql`, `parse_filters` (Task 1); `missing_days` table (Phase 1)
- Produces: `compute_stats(conn, f: VisitFilters) -> dict` with keys `total_visits, range, missing_days, by_weekday, by_hour, busiest_days, busiest_hours, visit_length` (shapes in Global Constraints). Identical for both roles: aggregates only, no `identities` flag.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_stats_api.py
import pytest

from tests.conftest import as_user


@pytest.fixture
def viewer(client):
    return as_user(client, "sam.ferreira@brightline.example")


def stats(client, headers, query=""):
    r = client.get(f"/api/stats{query}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_whole_dataset(client, viewer):
    s = stats(client, viewer)
    assert s["total_visits"] == 1953
    assert s["range"] == {"from": "2026-07-01", "to": "2026-09-30"}
    assert s["missing_days"] == ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"]
    assert s["busiest_days"] == ["Tuesday", "Wednesday"]
    assert s["busiest_hours"] == [9]
    assert s["visit_length"] == {"median_min": 79, "measured_visits": 1083, "total_visits": 1953}


def test_weekday_averages_use_operating_days(client, viewer):
    by_day = {d["name"]: d for d in stats(client, viewer)["by_weekday"]}
    assert list(by_day) == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    assert (by_day["Wednesday"]["visits"], by_day["Wednesday"]["operating_days"], by_day["Wednesday"]["avg_per_day"]) == (509, 13, 39.2)
    assert (by_day["Tuesday"]["operating_days"], by_day["Tuesday"]["avg_per_day"]) == (12, 39.6)


def test_hours_include_empty_lunch_hour(client, viewer):
    assert stats(client, viewer)["by_hour"] == [
        {"hour": 9, "visits": 726}, {"hour": 10, "visits": 252}, {"hour": 11, "visits": 270},
        {"hour": 12, "visits": 0}, {"hour": 13, "visits": 241}, {"hour": 14, "visits": 230}, {"hour": 15, "visits": 234}]


def test_type_filter_changes_the_answer(client, viewer):
    s = stats(client, viewer, "?type=guest")
    assert (s["total_visits"], s["busiest_days"], s["busiest_hours"]) == (798, ["Wednesday", "Thursday"], [10, 11])


def test_range_clipped_and_gap_reported(client, viewer):
    s = stats(client, viewer, "?from=2026-08-01&to=2026-08-31")
    assert s["range"] == {"from": "2026-08-01", "to": "2026-08-31"}
    assert s["missing_days"] == ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"]
    assert s["total_visits"] == 494


def test_empty_selection_is_an_honest_200(client, viewer):
    for q in ("?from=2026-08-10&to=2026-08-13", "?from=2030-01-01&to=2030-12-31"):
        s = stats(client, viewer, q)
        assert (s["total_visits"], s["busiest_days"], s["busiest_hours"], s["visit_length"]["median_min"]) == (0, [], [], None), q


def test_stats_validate_like_visits(client, viewer):
    r = client.get("/api/stats?page=2", headers=viewer)
    assert r.status_code == 400 and r.json()["error"].startswith("Unknown filter: page")


def test_stats_need_a_session(client):
    assert client.get("/api/stats").status_code == 401
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_stats_api.py -q`
Expected: FAIL with 404 `No such endpoint: GET /api/stats`

- [ ] **Step 3: Implement `compute_stats`** with SQL `GROUP BY` for the counts (`weekday`, `hour`, distinct `visit_date` for operating days over the same date range **without** the type filter). Median uses `statistics.median` over the filtered `duration_min IS NOT NULL` values, then `round()`. The hour span is `SELECT MIN(hour), MAX(hour) FROM visits` (whole table). Range clipping: `max(from, data_first)`, `min(to, data_last)`. Weekday names come from `calendar.day_name`.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass, including the extended leak test

- [ ] **Step 5: Commit** `feat: /api/stats with per-operating-day weekday averages, hours, ties and gap reporting`

---

### Task 4: `GET /api/admin/users` + end-to-end curl check

**Files:**
- Create: `app/routes/admin.py`, `tests/test_admin_api.py`
- Modify: `app/main.py`, `tests/test_leak.py` (a viewer calling `/api/admin/users` must get 403, and the body must contain no allow-list names other than the viewer's own)

**Interfaces:**
- Consumes: `require_admin`, `get_conn` (Phase 2)
- Produces: `GET /api/admin/users` (shape in Global Constraints)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_admin_api.py
from tests.conftest import as_user, signup

SAM, DANA = "sam.ferreira@brightline.example", "dana.whitfield@brightline.example"


def test_admin_sees_allow_list_and_who_signed_up(client):
    as_user(client, SAM)
    admin = as_user(client, DANA)
    users = client.get("/api/admin/users", headers=admin).json()["users"]
    assert len(users) == 8
    assert [u["role"] for u in users] == ["admin"] * 3 + ["viewer"] * 5
    signed = {u["email"] for u in users if u["signed_up"]}
    assert signed == {SAM, DANA}
    assert set(users[0]) == {"email", "name", "role", "signed_up"}


def test_viewer_is_refused_by_the_api(client):
    r = client.get("/api/admin/users", headers=as_user(client, SAM))
    assert r.status_code == 403 and r.json() == {"error": "You don't have access to this."}


def test_admin_users_needs_a_session(client):
    assert client.get("/api/admin/users").status_code == 401
```

Add to `tests/test_leak.py`:
```python
def test_viewer_cannot_read_the_user_list(client):
    r = client.get("/api/admin/users", headers=as_user(client, SAM))
    assert r.status_code == 403 and "dana" not in r.text.lower()
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_admin_api.py tests/test_leak.py -q`
Expected: FAIL. 404 `No such endpoint`, so the 403 assertions fail.

- [ ] **Step 3: Implement** `app/routes/admin.py` (`LEFT JOIN users` for `signed_up`) and include the router.

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass

- [ ] **Step 5: Curl as the viewer, exactly as the reviewers will**

```bash
.venv/bin/uvicorn app.main:app --port 8765 &
curl -s -X POST localhost:8765/api/auth/signup -H 'content-type: application/json' -d '{"email":"sam.ferreira@brightline.example","password":"frontdesk-viewer"}'
T=$(curl -s -X POST localhost:8765/api/auth/login -H 'content-type: application/json' -d '{"email":"sam.ferreira@brightline.example","password":"frontdesk-viewer"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s "localhost:8765/api/visits?page_size=200" -H "Authorization: Bearer $T" | grep -ci "felix fischer\|ffischer\|cedar & pine\|aisha"
curl -s "localhost:8765/api/visits?type=interview&from=2026-08-01&to=2026-08-31" -H "Authorization: Bearer $T" | head -c 400
curl -s -i "localhost:8765/api/visits?to=2026-07-01&from=2026-08-01" -H "Authorization: Bearer $T" | grep -E '^HTTP|error'
curl -s -i localhost:8765/api/admin/users -H "Authorization: Bearer $T" | head -1
```
Expected: grep count `0`; the filtered call shows viewer-only fields; the bad range gives `HTTP/1.1 400` with the end-before-start message; admin users gives `HTTP/1.1 403`. Stop the server and `rm var/frontdesk.db`.

- [ ] **Step 6: Commit** `feat: /api/admin/users for admins only; viewer sweep covers every endpoint`

---

## Phase 3 done when
- `.venv/bin/python -m pytest -q` passes (48 + 7 + 11 + 8 + 4 ≈ 78).
- The leak sweep (`tests/test_leak.py`) is green and its admin control finds names.
- The curl run in Task 4 Step 5 gives a grep count of 0.
- `grep -rnE "2026|guest|interview|Engineering|brightline" app/` finds only the agreed refusal copy.
