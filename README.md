# The Front Desk

A small internal app for Brightline's workplace team. It shows who visited the building and when the lobby gets busy,
and it is strict about who can see what:

- **admins** (3 people) see everything, including visitor names, emails, companies and hosts
- **viewers** (5 people) see how busy it was: counts, dates, times, visit types, host teams. **Never a visitor's or host's identity**
- **everyone else** can't get in

**The rules live in the API, not the pages.** A viewer's responses don't contain identities at all, so there's
nothing to find with curl, in the network tab, or by editing a URL.

---

## Quick start

Needs Python 3.10+ (tested on 3.13). From the project folder:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # 1. install
.venv/bin/uvicorn app.main:app                                       # 2. run, then open http://127.0.0.1:8000
.venv/bin/python scripts/create_test_accounts.py                     # 3. in a second terminal: create the test logins
```

On start-up the server loads `data/*.csv` into SQLite (`var/frontdesk.db`, created automatically) and prints:
```
Loaded 8 allowed users (3 admin, 5 viewer)
Loaded 1953 visits from 2026-07-01 to 2026-09-30 (dropped 58 duplicate sign-ins)
No sign-ins recorded on: 2026-08-10, 2026-08-11, 2026-08-12, 2026-08-13
```

## Test logins

Nobody is pre-registered: people create their own account, and only emails on `data/allowed_users.csv` can.
`scripts/create_test_accounts.py` signs these two up through the normal sign-up endpoint (safe to run twice):

| Role | Email | Password |
|---|---|---|
| admin | `dana.whitfield@brightline.example` | `frontdesk-admin` |
| viewer | `sam.ferreira@brightline.example` | `frontdesk-viewer` |

Or sign up in the app at `/signup` with any listed email and a password of your own (8+ characters).
These passwords are for this exercise only. Accounts live in your local `var/frontdesk.db`, which is not in the repo.

## The two curl examples

**1. Log in.** You get a token back, also set as an `HttpOnly` cookie for the browser:
```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/login -H 'content-type: application/json' \
  -d '{"email":"sam.ferreira@brightline.example","password":"frontdesk-viewer"}'
```
```json
{"token":"<token>","user":{"email":"sam.ferreira@brightline.example","name":"Sam Ferreira","role":"viewer"}}
```

**2. A filtered visits call.** Interviews in August, as the viewer:
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login -H 'content-type: application/json' \
  -d '{"email":"sam.ferreira@brightline.example","password":"frontdesk-viewer"}' \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["token"])')
curl -s "http://127.0.0.1:8000/api/visits?type=interview&from=2026-08-01&to=2026-08-31&page_size=2" \
  -H "Authorization: Bearer $TOKEN"
```
Each item has `visit_id, date, signed_in, signed_out, duration_min, visit_type, host_team, pre_registered`, with
`"total": 115`. **There is no visitor or host in it.** The same call with the admin's token adds
`"visitor": {"name", "email", "company"}` and `"host": {"name", "email"}`.

**The reviewers' check.** Search a viewer's response for a visitor's name. Sofia Reyes is on the first page of visits,
so the admin's response contains her and the viewer's doesn't:
```bash
curl -s "http://127.0.0.1:8000/api/visits?page_size=200" -H "Authorization: Bearer $TOKEN" | grep -ci "sofia reyes"   # 0
```
To check every name in the data rather than one, and to see the admin's `1` side by side, see
[docs/TESTING_WITH_CURL.md](docs/TESTING_WITH_CURL.md) sections 5–6.

## The API in one table

Full spec, with every parameter, response and error: **[docs/API.md](docs/API.md)**. Interactive: `/docs`.

| Method and path | Who | What |
|---|---|---|
| `POST /api/auth/signup` | anyone | Create an account (access list only) |
| `POST /api/auth/login` | anyone | Start an 8-hour session (cookie, plus a Bearer token for curl) |
| `POST /api/auth/logout` | signed in | End it |
| `GET /api/me` | signed in | Who am I, can I see identities |
| `GET /api/visit-types` | signed in | Visit types in the data |
| `GET /api/visits?from&to&type&page&page_size` | signed in | Visits, filtered and paged on the server; fields depend on role |
| `GET /api/visits/:id` | signed in | One visit; fields depend on role |
| `GET /api/stats?from&to&type` | signed in | By weekday, by hour, both, busiest, visit length, missing days |
| `GET /api/admin/users` | admin | The access list and who signed up |

Status codes:
- no session → JSON **401** (never a redirect)
- viewer on an admin endpoint → **403**
- bad input → **400** with a message a person can act on (never a 500 or an empty 200)

## The pages

`/login`, `/signup`, `/visits` (where you land), `/visits/:id`, `/admin/users` (admins), and a real "Page not found"
for anything else.

- **Every page has its own URL** and survives a refresh.
- **Filters live in the URL**, so a filtered link pasted to a colleague opens filtered.
- If you're signed out, you go to sign in and then come back to where you were going.
- A viewer typing `/admin/users` gets a clean "You don't have access" page, and the nav never offers them that link.

The route guard is a courtesy. **The API's 403 is the real control.**

## Tests

| Suite | Command | Expect |
|---|---|---|
| Python (API, loader, auth, leak sweep) | `.venv/bin/python -m pytest` | all pass |
| JavaScript (page logic) | `node --test 'tests/js/*.test.mjs'` (Node 22+) | `fail 0` |
| Security checks with curl (app running) | `scripts/security_check.sh` | `30 passed, 0 failed` |
| Real browser (Chrome installed) | `scripts/browser_check/serve-fresh.sh && node scripts/browser_check/run.mjs` | `52 passed, 0 failed` |

The browser and security suites are described in [scripts/README.md](scripts/README.md). An independent security
reviewer can start from [docs/SECURITY_TESTS.md](docs/SECURITY_TESTS.md) alone.

## Decisions

- **What a refused person is told:** *"This email isn't on Brightline's access list. If you think it should be, ask
  Dana."* It's friendly on purpose. The people refused are mostly colleagues who mistyped, and the cost to a stranger
  is learning that an email isn't on an 8-person list. Login failures, by contrast, are all the same generic message.
- **What a viewer sees where a name would be:** nothing. Viewers don't get a visitor column or a placeholder; their
  question is how busy it was. A single visit is titled by its type ("Guest"), not by a person.
- **Host names are hidden from viewers too.** They see the host's team. Hosts are named people, and 60 host names are
  also visitor names in this data.
- **Emails match the way a person would expect:** case and stray spaces are ignored. Two of the three admins in the
  export have capitals or spaces in their email.
- **Data problems are handled, not hidden.**
  - 58 duplicate sign-ins are removed.
  - The four days with no data (10–13 Aug) are flagged on every page that includes them.
  - Busiest day is averaged per day with data.
  - Visit length is a median of the visits that have a sign-out.

  See [docs/DATA_NOTES.md](docs/DATA_NOTES.md).
- **All endpoints are under `/api`** (the brief suggested `/auth/*` for sign-in). One prefix means "JSON"; every other
  path is a page.

## What's fake

Accounts and sessions live in a local SQLite file. Passwords are hashed (scrypt) and session tokens are stored hashed,
but there's no HTTPS, no email verification, no password reset, and there are two published test logins. With real
visitors' data, I'd put it behind the company's single sign-on, log who viewed names, set a retention period, and serve it over HTTPS.
More in the note to Dana: [docs/NOTE_TO_DANA.md](docs/NOTE_TO_DANA.md).

## Project layout

```
app/        the API: loading the CSVs, auth, role-aware queries, errors       → app/README.md
static/     the pages: one shell, a small router, design tokens               → static/README.md
tests/      pytest suites, JS unit tests, the viewer leak sweep               → tests/README.md
scripts/    test logins, security checks, browser checks, data audit          → scripts/README.md
data/       the two CSVs (never modified)
docs/       API spec, testing guides, data notes, note to Dana, plans
```

## Documentation

| Doc | For |
|---|---|
| [docs/API.md](docs/API.md) | The complete API spec |
| [docs/TESTING_WITH_CURL.md](docs/TESTING_WITH_CURL.md) | Proving a viewer's payload has no identities, step by step |
| [docs/NETWORK_TAB_CHECK.md](docs/NETWORK_TAB_CHECK.md) | The same check in the browser's network tab |
| [docs/SECURITY_TESTS.md](docs/SECURITY_TESTS.md) | A self-contained brief for an independent security review |
| [docs/DATA_NOTES.md](docs/DATA_NOTES.md) | What's wrong with the two files and how it's handled |
| [docs/NOTE_TO_DANA.md](docs/NOTE_TO_DANA.md) | The note to Dana |
| [docs/plan.md](docs/plan.md) | The original plan and design system |
