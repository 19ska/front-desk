# Phase 5: Documentation, Security Test Kit and Hand-off Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Everything a reviewer, a friend, Dana and an independent security agent need. That means working test logins, a complete API spec, a curl guide that proves a viewer's payload has no identities, a network-tab guide, a self-contained security-test brief with a runnable script, a README for every folder, the note to Dana, a final run of the brief's done-when checklist, and a clean zip.

**Architecture:** Documentation lives in `docs/`, with one README per code folder. Anything a document tells someone to run is also **executed by this plan**, so no command in the docs is untested:
- every curl example ships as a runnable `scripts/security_check.sh`, which the docs quote and this plan runs against a fresh server
- a pytest keeps `docs/API.md` in step with the real routes

**Tech Stack:** Markdown, bash + curl + python3 (stdlib only) for the security script, the existing pytest / node / headless-Chrome suites.

**Spec:** The brief (`.claude/specs/The Front Desk - Take-Home.html`, sections 03–08), `docs/plan.md` sections 2 and 9, and `docs/DATA_NOTES.md`.

## Global Constraints

- **Test logins** (documented in the README, as the brief asks):
  - admin `dana.whitfield@brightline.example` / `frontdesk-admin`
  - viewer `sam.ferreira@brightline.example` / `frontdesk-viewer`

  They're created by an opt-in script that goes through the normal sign-up endpoint. Nobody is pre-registered in the data.
- The viewer test account is Sam because Sam's name doesn't appear in the visit data (DATA_NOTES V7). Using Kenji, for example, would make a name grep find the viewer's own name in `/api/me`. Every doc that greps says this.
- Docs use only commands that work on a stock macOS or Linux shell: `curl`, `python3`, `grep`. No `jq`.
- Base URL in every doc is `http://127.0.0.1:8000`, overridable with `BASE=...`.
- Project root keeps only `README.md`, `requirements.txt`, `.gitignore` and folders.
- The zip is built with `git archive` (no `.git`, no `var/`, no `.venv/`) at `~/Desktop/front-desk.zip`, outside the project.
- The note to Dana is written to Dana, in her language: no code terms, no field names.
- Exact copy and status codes come from the code as it stands (Phases 1–4). The docs describe, they don't redefine.

## Review Focus

1. **A doc command that doesn't run** (typo, wrong path, missing `-H`). Every command in `docs/TESTING_WITH_CURL.md` and `docs/SECURITY_TESTS.md` must appear in, or be exercised by, `scripts/security_check.sh`, which Task 3 runs green.
2. **The API spec drifting from the code.** `tests/test_docs.py` fails if any `/api` route is missing from `docs/API.md`.
3. **The test-accounts script run twice, or after someone already signed up.** It must say "already exists" and exit 0, not crash.
4. **A reviewer grepping with a viewer whose name is in the data.** The curl guide explains why it uses Sam and shows how to grep for every name, not just one.
5. **Following the README from a fresh clone of the zip** (no `var/`, no `.venv/`) must work exactly as written. Test in Task 6 by unzipping into a temp folder and following the README word for word.

---

## File Structure

| File | Who it's for | Contents |
|---|---|---|
| `README.md` | reviewers, your friend | What it is; quick start (setup, run, test logins); the brief's **two curl examples** (login, filtered visits); where the access rules live; endpoint summary linking to `docs/API.md`; how to run every test suite; project layout; the decisions made (refusal wording, what viewers see, host names hidden, `/api` prefix); what's fake / what we'd do with real data; documentation index |
| `docs/API.md` | anyone calling the API | **Complete spec**: base URL; auth (cookie `fd_session` or `Authorization: Bearer`; 8 h sessions; role read per request); error format; status codes. For every endpoint: method, path, auth, parameters (type, format, default, limits), request body, response for **viewer and admin** (real JSON examples), every error with its exact message. Plus the field glossary, filter rules (inclusive dates, unknown parameter → 400), stats definitions (operating days, ties within 5%, median) |
| `docs/TESTING_WITH_CURL.md` | a person checking by hand | Start the server on a fresh DB, create the test logins, then step by step: log in as viewer and admin; **compare the same request as viewer vs admin** (field lists printed side by side); the **full leak check**, which pulls every visitor name, email, company, host name and host email out of the CSV and greps every page of the viewer's responses for them (expected: 0); single visit; stats; the admin endpoint as viewer (403); no session (401); the bad inputs from the brief (400s); "why Sam, not Kenji" |
| `docs/NETWORK_TAB_CHECK.md` | a person checking in a browser | Chrome/Edge and Firefox steps: open DevTools → Network → Fetch/XHR → sign in as Sam → open Visits. Then click the `visits?…` request → Response/Preview, and use **Search across all responses** (⌘⌥F / Ctrl+Shift+F) for a known visitor ("Sofia Reyes", `oakfieldlega`), expecting 0 results. Repeat on a single visit and on stats. Then sign in as Dana to see the same search find them, which shows the check can work. Also "Copy as cURL". Screens to expect, described in words |
| `docs/SECURITY_TESTS.md` | **an independent agent, with no other context** | Mission and scope; what the app must guarantee (the brief's rules quoted); environment requirements; setup from a fresh copy (exact commands); accounts; where the code is (file map); the automated suites and exact commands with expected outputs; a **test catalogue** (ID, what to try, command, expected result); a list of things that are out of scope by design; rules of engagement (localhost only, never edit app code, write findings to a new file); the report format (`docs/SECURITY_FINDINGS.md`, a severity scale and a template) |
| `docs/NOTE_TO_DANA.md` | Dana | What I found in your files; who can see what and why; what's fake here; what I'd do next |
| `scripts/create_test_accounts.py` | everyone | Opt-in. Signs up the two test logins through `POST /api/auth/signup` on a running server (`--base`, default `http://127.0.0.1:8000`). Already exists → says so and continues. Server not running → clear message, exit 1 |
| `scripts/security_check.sh` | humans and the agent | Runnable curl suite: PASS/FAIL per check and a summary, exit 1 on any failure. Implements catalogue items S1–S30 that curl can reach |
| `scripts/README.md` | developers | What each script is, when to run it, and the commands |
| `scripts/data_audit/README.md`, `scripts/browser_check/README.md` | developers | Purpose, how to run, what output means |
| `app/README.md` | code readers | Module map ("where the rules live"), request flow, the two key security points (role-projected SELECT; role read per request) with file:line pointers |
| `static/README.md` | code readers | Frontend map: shell, router, pages, components, lib, design tokens; the `h()` text-only rule; Web Awesome usage |
| `tests/README.md` | developers | The suites, what each file covers, the leak sweep and its admin control, how to run |
| `tests/test_docs.py` | CI | Every API route appears in `docs/API.md`; the README's two test logins match `scripts/create_test_accounts.py` |

---

### Task 1: Test-account script + API spec + doc/route sync test

**Files:** create `scripts/create_test_accounts.py`, `docs/API.md`, `tests/test_docs.py`

**Interfaces:**
- `scripts/create_test_accounts.py [--base URL]`. Stdlib `urllib` only. It exposes `TEST_ACCOUNTS = [("dana.whitfield@brightline.example", "frontdesk-admin", "admin"), ("sam.ferreira@brightline.example", "frontdesk-viewer", "viewer")]`. Output lines are one of:
  - `Created admin login dana.whitfield@brightline.example`
  - `Already exists: dana.whitfield@brightline.example`
  - `Can't reach the app at <base>. Start it first: .venv/bin/uvicorn app.main:app`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_docs.py
import re
from pathlib import Path

from app.main import create_app

API_DOC = Path("docs/API.md")


def api_routes(tmp_path):
    app = create_app(db_path=tmp_path / "t.db")
    found = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/") and "{rest" not in path:
            for method in getattr(route, "methods", set()) - {"HEAD"}:
                found.add(f"{method} {path}")
    return found


def test_every_api_route_is_documented(tmp_path):
    doc = API_DOC.read_text()
    missing = [r for r in sorted(api_routes(tmp_path)) if r.replace("{visit_id}", ":id") not in doc and r not in doc]
    assert missing == []


def test_readme_logins_match_the_account_script():
    readme = Path("README.md").read_text()
    script = Path("scripts/create_test_accounts.py").read_text()
    for email, password in re.findall(r'\("([^"]+@[^"]+)", "([^"]+)", "(?:admin|viewer)"\)', script):
        assert email in readme and password in readme, email
```

- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_docs.py -q`. Expected: FAIL (`docs/API.md` missing).
- [ ] **Step 3: Write** `docs/API.md`. Generate the example JSON by actually calling the running app as Sam and Dana (trimmed to one item); never type examples by hand. Write `scripts/create_test_accounts.py` and the README test-login section (a minimal README is enough for this task; Task 4 completes it).
- [ ] **Step 4: Run** the full pytest suite. Expected: all pass. Run the script twice against a fresh server: the first run prints "Created …" twice, the second prints "Already exists …" twice, and both exit 0. With the server stopped, it prints the can't-reach line and exits 1.
- [ ] **Step 5: Commit** `docs: complete API spec, opt-in test-account script, doc/route sync test`

---

### Task 2: The executable security suite

**Files:** create `scripts/security_check.sh`

**Behaviour:** `BASE=http://127.0.0.1:8000 scripts/security_check.sh`. It needs the two test logins to exist and runs `create_test_accounts.py` first. It uses `python3` to pull identities from `data/visits.csv` and to read JSON. Each check prints `PASS  S<n>  <description>` or `FAIL  S<n>  <description> (<detail>)`. It ends with `N passed, M failed` and exits 1 on any failure.

**Catalogue it implements** (the same IDs are used in SECURITY_TESTS.md):

| ID | Check | Expected |
|---|---|---|
| S1 | Every data endpoint with no session | 401, JSON `{"error": "Sign in to continue."}`, `content-type: application/json` |
| S2 | Garbage / malformed Bearer, garbage cookie | 401 |
| S3 | Viewer: all pages of `/api/visits?page_size=200` grepped for **every** visitor name, visitor email, company, host name, host email in the CSV | 0 matches |
| S4 | Viewer: `/api/visits/<id>` for 50 ids spread across the file | 0 matches; no `"visitor"` or `"host"` key |
| S5 | Viewer: `/api/stats` (all, per type, August) | 0 matches |
| S6 | Viewer vs admin, same request: key sets | viewer item keys exactly `visit_id,date,signed_in,signed_out,duration_min,visit_type,host_team,pre_registered`; admin adds `visitor,host` |
| S7 | Viewer identity-shaped parameters (`visitor_name`, `q`, `sort`, `visitor_email`, `host_name`, `company`) | 400 `Unknown filter: …` |
| S8 | Viewer `GET /api/admin/users` | 403 `You don't have access to this.`, body contains no allow-list names |
| S9 | Admin `GET /api/admin/users` | 200, 8 users |
| S10 | Sign-up with an email not on the list | 403 with the agreed refusal |
| S11 | Sign-up with messy case/spaces for a listed email (`" Ruth.Grant@BRIGHTLINE.example "`) | 201 on a fresh server (409 on a re-run), and then login with `ruth.grant@brightline.example` works |
| S12 | Sign-up twice | 409 |
| S13 | Login failures (wrong password / unknown email / listed-but-not-signed-up) | all 401 with the identical message |
| S14 | Login sets cookie flags | `HttpOnly`, `SameSite=Lax`, `Max-Age=28800`, `Path=/` |
| S15 | Logout then reuse the token | 401 |
| S16 | Bad dates (`14/08/2026`, `2026-02-30`), end before start, unknown type, `page=0`, `page=999`, `page=` 5000 digits, `page_size=500`, repeated `type` | 400 each with the exact message; never 500 |
| S17 | SQL-shaped input in `type`, `from`, `id` (`' OR 1=1--`, `1;DROP TABLE visits`) | 400 or 404; afterwards `/api/stats` total is still 1953 |
| S18 | Non-JSON / empty / list body on signup and login | 400 with an actionable message |
| S19 | Lone-surrogate text in JSON | 400 |
| S20 | Unknown `/api` path with GET and POST | 404 JSON |
| S21 | Unknown page path | 404 status, HTML shell |
| S22 | Known page path without a session | 200 shell. The shell contains no data: grep it for identities, expecting 0 |
| S23 | `/openapi.json` and `/docs` | reachable (documented as intentional), and they contain no visitor data |
| S24 | No CORS header for a foreign `Origin` | no `access-control-allow-origin` in the response |
| S25 | Very long id / odd ids (`%2e%2e`, a 5,000-character id) | 404, no 500 |
| S26 | Dedup id `V001996` as viewer and admin | identical 404 bodies |
| S27 | Admin can see names | the S3 grep finds > 50 names for admin (proves S3 can detect a leak) |
| S28 | Headers on the HTML shell | no server stack traces; content-type `text/html` |
| S29 | Response size sanity: the viewer's biggest list page | ≤ 200 items |
| S30 | Stats identical for viewer and admin | byte-identical JSON |

- [ ] **Step 1:** Write the script.
- [ ] **Step 2:** Start a fresh server (`scripts/browser_check/serve-fresh.sh` is on 8765, so run with `BASE=http://127.0.0.1:8765`) and run the script. Expected: all PASS. Any FAIL is a real defect: switch to `superpowers:systematic-debugging`, fix it test-first in pytest, then re-run.
- [ ] **Step 3: Commit** `test: executable curl security suite (S1–S30)`

---

### Task 3: The two human guides

**Files:** create `docs/TESTING_WITH_CURL.md`, `docs/NETWORK_TAB_CHECK.md`

- [ ] **Step 1:** Write `TESTING_WITH_CURL.md`.
  - Every command block is copy-pasteable and uses `$BASE` and `$T_VIEWER` / `$T_ADMIN` variables set earlier in the doc.
  - The **leak check** is one block: it extracts the identities with `python3 -c`, fetches all 10 pages, and runs `grep -ciF -f`, with expected output `0`.
  - Admin vs viewer is shown with a one-liner that prints both key lists.
  - Each step says **what you should see**.
  - It ends with "run it all at once: `scripts/security_check.sh`".
- [ ] **Step 2:** Write `NETWORK_TAB_CHECK.md`.
  - Numbered steps for Chrome/Edge, plus notes for Firefox and Safari: where the panel is, how to filter to Fetch/XHR, and how to open the Response/Preview tab.
  - How to use **Search across all network responses**: Chrome ⌘⌥F (Mac) or Ctrl+Shift+F, with the funnel/search icon in the Network panel. Make sure "Preserve log" is on.
  - Which names to search for. Pick three from the first page of the admin view, e.g. Clara Haddad, Sofia Reyes and the company Oakfield Legal, and explain that any name from the CSV works.
  - The control experiment: the same steps as Dana find the names.
  - Then check `/api/visits/V001912` and `/api/stats`.
  - Then try editing the URL: `/visits?visitor_name=Sofia` gives the API's 400 message on the page.
  - **Why hiding a column isn't enough, and why this app passes:** the page never receives the data.
- [ ] **Step 3:** Run every command block in `TESTING_WITH_CURL.md` by hand against a fresh server (copy them into a temp shell script; don't edit the doc to make them pass unless the doc is wrong). Expected outputs match the doc. Walk through `NETWORK_TAB_CHECK.md` in headless Chrome as far as the protocol allows: confirm the visits response body as Sam contains none of the three example names, and as Dana it does.
- [ ] **Step 4: Commit** `docs: curl testing guide and network-tab check`

---

### Task 4: READMEs for everything + the security brief for an independent agent

**Files:** complete `README.md`; create `docs/SECURITY_TESTS.md`, `app/README.md`, `static/README.md`, `tests/README.md`, `scripts/README.md`, `scripts/data_audit/README.md`, `scripts/browser_check/README.md`

- [ ] **Step 1:** Write `README.md`. It must contain:
  - quick start in **at most 4 commands**
  - both test logins
  - the brief's 2 curl examples, verbatim and runnable
  - every suite's run command
  - the documentation index linking all other docs
- [ ] **Step 2:** Write `docs/SECURITY_TESTS.md` so that an agent with **only this file and the repo** can do the job. Sections, in order:
  1. Mission
  2. The guarantees under test (the brief's rules, quoted)
  3. Requirements: Python ≥ 3.11, Node ≥ 22, Google Chrome for the browser suite, curl
  4. Setup from a fresh copy (exact commands, ports)
  5. Accounts
  6. Code map: where auth, the role projection, filters, errors and pages live (file paths)
  7. How to run each suite, with the expected summary line:
     - `pytest` → `N passed`
     - `node --test` → `fail 0`
     - `scripts/security_check.sh` → `30 passed, 0 failed`
     - `scripts/browser_check/run.mjs` → `52 passed, 0 failed`
  8. The S1–S30 catalogue (the same table as above, with the command for each), plus **B1–B10 browser-side checks**: `next=` redirect variants, XSS via `h()`, network-tab leak, refresh/deep links, route guard vs API, and the stale-tab note
  9. Things worth probing beyond the catalogue
  10. Out of scope by design: rate limiting, HTTPS, CSRF beyond `SameSite=Lax`, password reset, small-count re-identification (documented in the note to Dana), the deferred minors from Phases 2–4
  11. Rules of engagement: localhost only, never modify `app/` or `static/`, write throwaway scripts under `/tmp`, don't commit
  12. Report format: write `docs/SECURITY_FINDINGS.md` with a summary, a table (ID, severity Critical/High/Medium/Low/Info, endpoint or page, steps, expected, actual, evidence), and a list of what was tested and passed
- [ ] **Step 3:** Write the folder READMEs (short: purpose, map, run commands, gotchas). `app/README.md` points at the exact lines of `app/visits.py` (column lists), `app/auth.py` (`resolve_session` join) and `app/deps.py` (`require_admin`).
- [ ] **Step 4:** Run `.venv/bin/python -m pytest -q` (the docs test stays green). Check every relative link in the docs resolves (a one-off `python3` check over `](…)` targets).
- [ ] **Step 5: Commit** `docs: READMEs for every folder and a self-contained security test brief`

---

### Task 5: The note to Dana

**Files:** create `docs/NOTE_TO_DANA.md`

**Content** (to Dana, plain words, about one page):
- **What I found in your files.**
  1. Two of the three admins would have been locked out by an exact email match (capitals, spaces).
  2. 58 sign-ins were recorded twice by the iPad. They're removed, which leaves 1,953 visits.
  3. No sign-ins at all from Mon 10 to Thu 13 August. Was the iPad down? The app says so wherever those days are included.

  Plus, briefly: 45% of guests never sign out, so visit length is a median of those who did. The 9 am rush is your interview schedule (without interviews, 11 am is busiest). Tuesday and Wednesday tie once you count per day. Three hosts appear under two teams.
- **Who can see what, and why.**
  - Three people see names, five see counts, everyone else is refused.
  - The rules are enforced by the server, not the page.
  - Viewers don't see a stand-in for the visitor at all.
  - Host names are hidden from viewers too.
  - The refusal message wording, and why it's friendly.
- **What's fake here:** accounts and sessions live in a local file, passwords are hashed but there's no HTTPS, email reset or SSO, and two test logins exist.
- **What I'd do with real visitors' data:** SSO instead of passwords, an audit log of who viewed names, a retention period, suppressing very small counts, and HTTPS.
- **Questions for you:** the August gap, the lunch hour, the three hosts' teams, the time zone.
- **What I'd do next.**

- [ ] **Step 1:** Write it.
- [ ] **Step 2:** Check every number in it against `/api/stats` and DATA_NOTES (1,953; 58; 45%; Tue/Wed; 9 am; 11 am).
- [ ] **Step 3: Commit** `docs: note to Dana`

---

### Task 6: Done-when checklist, fresh-clone test, zip

- [ ] **Step 1:** Run every suite on a fresh server and record the summary lines in the ledger: pytest, node, `security_check.sh`, browser `run.mjs`.
- [ ] **Step 2:** Walk the brief's "You're done when" list (section 08), one line each with its evidence (the suite and check ID that proves it).
- [ ] **Step 3: Fresh-clone test.**
  - `git archive --format=zip -o ~/Desktop/front-desk.zip HEAD`.
  - Unzip it into a new temp folder and follow `README.md` exactly: venv, install, run, create logins, both curl examples, `security_check.sh`.
  - Every step must work; fix the README if not.
  - Then delete the temp folder.
- [ ] **Step 4:** Confirm the zip contains no `.git`, `var/`, `.venv/`, `.claude/` or `.superpowers/`, and list its top level.
- [ ] **Step 5: Commit** any README fixes. Don't commit the zip.

---

## Phase 5 done when
- All four suites are green: pytest, node, `security_check.sh` 30/30, and browser 52/52.
- Every command in every doc has been run and matches the doc.
- `~/Desktop/front-desk.zip` exists, and a fresh unzip works by following the README alone.
- `docs/SECURITY_TESTS.md` is complete enough that an agent needs nothing else.
