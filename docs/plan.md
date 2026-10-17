# The Front Desk — Build Plan

> Source brief: `.claude/specs/The Front Desk - Take-Home.html`
> Time budget: **3 hours max** (a ceiling, not a target). Due within 3 days.
> Status: **stack chosen (Option B: Python FastAPI + SQLite + vanilla JS). Waiting on the CSVs for Phase 0.**

---

## 1. What we're building, in one paragraph

Brightline's workplace team (Dana + 2 others) wants a small internal web app over three months of lobby
sign-ins (`visits.csv`, 2,011 rows). **3 admins** see everything, including visitor names, emails, companies
and hosts. **5 viewers** see only how busy the building is: counts, dates, host teams and visit types, and never
a visitor's identity. Everyone else is refused. The access rules are the reason the app is allowed to exist,
so **they live in the API, not the UI**. The reviewers will curl the visits endpoint as a viewer and search
the raw response for a visitor's name. That test decides most of the grade.

### What's graded (and what isn't)
| Graded | Not graded |
|---|---|
| Access control enforced in the API (viewer can't reach a name by **any** route) | Test coverage |
| API design: status codes, validation, server-side filtering, README-usable | Architecture / framework choice |
| URLs behave: refresh, back, share a filtered link | Visual polish, charts, mobile, dark mode |
| Finding the 2 data problems before they break a number | Crypto quality |
| The note to Dana: plain language, reasoned decisions | Docker, HTTPS, cloud, rate limiting |

---

## 2. Non-negotiables (from the brief, turned into checks)

These go into the final verification checklist (Phase 6). Each one maps to a test we run ourselves.

**Auth**
- [ ] Sign-up only for emails on `allowed_users.csv`. Everyone else gets a clear refusal (no crash, no blank page).
- [ ] Email matching is forgiving: trim whitespace, compare case-insensitively (plus whatever else the data audit turns up).
- [ ] Every one of the 8 listed people can sign up. Nobody else can.
- [ ] One admin + one viewer test login in the README.

**API**
- [ ] No data without a valid session. Unauthenticated → **401 JSON** (never an HTML redirect).
- [ ] A viewer's payload contains **no visitor name or email anywhere**: not hidden, not nulled, *absent*.
- [ ] Filtering, paging and counting happen server-side. Never ship all 2,011 rows.
- [ ] Bad input → **400** with a human-actionable message (end before start, unknown visit type, bad id). Never 500, never an empty 200.
- [ ] Works from curl. README has two worked examples: login + filtered visits call.
- [ ] Admin-only endpoints (users list) return **403** to viewers.

**Pages**
- [ ] `/login`, `/signup`, `/visits`, `/visits/:id`, `/admin/users`, and a real 404.
- [ ] Refresh on any page (including a single visit) keeps you there, still signed in.
- [ ] Filters live in the URL (`/visits?type=interview&from=2025-08-01&to=2025-08-31`). Pasted links open filtered.
- [ ] Not signed in → login → **back to the page you wanted**.
- [ ] Signed in but not allowed → clean "you don't have access" page. Viewers never see a nav link that bounces them.
- [ ] Honest loading / empty states, including a plain-words warning for any period where the data is unreliable.

---

## 3. Phase 0 first: the data audit (do this before writing app code)

The brief says outright: *one problem is in the visit data, one is in the user list.* We'll find them with a
small throwaway script once the CSVs arrive. **Write the findings down as we go; they become part of the note to Dana.**

### 3a. `allowed_users.csv` (8 rows: email, name, role). Things to check
| Check | Why it matters | Likely fix |
|---|---|---|
| Leading/trailing whitespace, mixed case in emails | "Locked out by a capital letter is a bug" | Normalise: `trim().toLowerCase()` at load **and** at signup/login |
| Duplicate email (possibly with *conflicting* roles, e.g. admin and viewer) | Which role wins? | **Least privilege**: take the lower role, flag it in the note, ask Dana |
| Role values not exactly `admin`/`viewer` (`Admin`, ` viewer`, blank, `editor`) | Silent mis-grant | Normalise case/space; unknown role → **no access** (fail closed) and log it |
| Count of admins ≠ 3 / viewers ≠ 5 | Brief says 3 + 5; mismatch means a data error | Report to Dana |
| Different-domain or typo'd addresses, Unicode lookalikes, trailing dots | Odd export artefacts | Decide case by case and document it |
| Header/BOM/encoding oddities | Breaks the first column name | Strip BOM on load |

### 3b. `visits.csv` (2,011 rows). Things to check
| Check | Why it matters | Likely fix |
|---|---|---|
| A date range where `signed_out_at` is missing/blank/identical/before sign-in | Brief hints at "a period where the data can't be relied on" | Exclude that period from duration stats and show a plain-words banner ("Sign-out times weren't recorded between X and Y, so visit lengths for those days are left out") |
| Duplicate rows / duplicate `visit_id` (iPad double-submits) | Inflates the busiest-day/hour numbers | De-duplicate on load and report how many |
| Timestamp format & time zone (UTC `Z` vs local, mixed formats) | "Busiest hour" is wrong if UTC is shown as local | Parse explicitly; bucket hours in the office's local time zone (confirm with Dana) |
| `visit_date` disagreeing with the date part of `signed_in_at` | Filters and stats disagree | Pick one source of truth (signed_in_at, local) and note it |
| `visit_type` spelling/case variants (`Interview`, `interview `) | Breaks the filter and the counts | Normalise; build the allowed type list from cleaned data |
| Test/junk rows (e.g. "test", staff testing the iPad) | Skews counts | Exclude and report |
| Weekend / out-of-hours spikes, impossible dates | Sanity check | Investigate |
| `pre_registered` values (`TRUE/true/1/yes`) | Boolean parsing | Normalise |

**Output of Phase 0:** ✅ done. Scripts in `scripts/data_audit/`, findings and decisions in `docs/DATA_NOTES.md`.
Summary: emails with caps and spaces (2 of 3 admins), 58 duplicate double-tap sign-ins, no data 10–13 Aug, 45% never
sign out, and busiest day is a Tue/Wed tie only if you average per day properly.

### Project layout (keep the root clean)
```
project-001/
├── data/                  # the two CSVs (input, never modified)
├── docs/                  # plan.md, DATA_NOTES.md, NOTE_TO_DANA.md
├── scripts/data_audit/    # audit scripts (+ verify_a/, verify_b/ from independent checks)
├── app/                   # FastAPI backend (main.py, auth.py, db.py, loader.py, routes/)
├── static/                # index.html, css/ (tokens.css, app.css), js/, vendor/, fonts/
├── tests/                 # pytest + the viewer leak test
└── README.md, requirements.txt, .gitignore   # the only files at root
```
If anything is ambiguous, **email "Dana" on day one**. The brief says asking counts in our favour.

---

## 4. Tech stack options (pick one)

All options share the same shape: **one local process** serves both the JSON API and the pages, with the
CSVs loaded into **SQLite** at startup. SQLite is the right database for every option. It's file-based with
zero setup, does real SQL `GROUP BY` for the stats (server-side counting for free), and gives us a `users`
and `sessions` table without a server. (An in-memory list also works, but SQL makes "only select the columns
this role may see" explicit and easy to show on the review call.)

### Option A: Node + TypeScript, Express, SQLite, React (Vite) SPA  ⭐ *recommended if you're comfortable in JS/TS*
| Piece | Library |
|---|---|
| Server | `express` (or `fastify`) |
| DB | `better-sqlite3` (synchronous and simple, no async noise) |
| CSV | `csv-parse` |
| Validation | `zod` (one schema → clean 400 messages) |
| Passwords | `bcryptjs` (or Node's built-in `crypto.scrypt`, so no dependency) |
| Sessions | random token (`crypto.randomBytes`) in a `sessions` table, sent as an httpOnly cookie **and** accepted as `Authorization: Bearer` for curl |
| Frontend | Vite + React + `react-router` (history routes), built to `dist/` and served by Express with an `index.html` fallback |
| Leak test | `vitest` + `supertest`, or a plain bash script with `curl` + `grep` |

**Pros:** one language end to end; React Router gives us URL-driven filters (`useSearchParams`), deep links and
"return to where you were" almost for free; huge ecosystem, and AI tools are strong at it; easy to explain.
**Cons:** two build pieces (Vite + server), so dev runs two processes with a proxy or needs a build step;
TypeScript setup costs ~10 min; more files to explain than a vanilla app.

### Option B: Python, FastAPI, SQLite, plain HTML + vanilla JS
| Piece | Library |
|---|---|
| Server | `fastapi` + `uvicorn` |
| DB | stdlib `sqlite3` |
| CSV / audit | stdlib `csv` (or `pandas` for the Phase 0 audit only) |
| Validation | Pydantic (built into FastAPI) |
| Passwords | `passlib[bcrypt]` or stdlib `hashlib.scrypt` |
| Sessions | token in a `sessions` table, httpOnly cookie + Bearer |
| Frontend | static HTML + a ~100-line vanilla JS router (History API) served by FastAPI, or `htmx` |
| Tests | `pytest` + FastAPI `TestClient` |

**Pros:** smallest, most readable backend; auto-generated `/docs` (OpenAPI), which makes "API a stranger can
use" nearly free; pandas makes the data audit fast; fewest moving parts.
**Cons:** FastAPI returns **422** for validation errors by default, so we must override it to **400** (easy but
easy to forget); the vanilla-JS router is hand-rolled (more of our own code to get right for refresh/back/redirect-after-login);
two languages if you're not already comfortable in Python.

### Option C: Next.js (App Router) full-stack
| Piece | Library |
|---|---|
| Everything | Next.js route handlers for the API, pages for UI, `better-sqlite3`, `zod`, `iron-session` or a hand-rolled cookie |

**Pros:** one framework and one process; file-based routing gives every page an address and a 404 automatically.
**Cons:** **riskiest for this task.** Server Components, middleware and client components blur the
server/client line, which is exactly where a name can leak into the page payload (RSC payloads, props
serialisation). Middleware route guards *look* like security but aren't the real control. Heavier and
more "magic" to explain on the code-reading call. Overkill for 3 hours.

### Option D: Go (net/http) + SQLite + vanilla JS
**Pros:** single binary, explicit and fast, stdlib does most of it (Go 1.22 router has path params).
**Cons:** more boilerplate for JSON/validation; `sqlite` driver needs CGO (`mattn/go-sqlite3`) or the pure-Go `modernc.org/sqlite`; slower to iterate in a 3-hour box unless Go is your daily language.

### Quick comparison
| | A: Node/React | B: FastAPI/vanilla | C: Next.js | D: Go |
|---|---|---|---|---|
| Time to working API | Fast | **Fastest** | Medium | Medium |
| URL/refresh/back behaviour | **Easiest** (React Router) | Hand-rolled | Easy | Hand-rolled |
| Risk of accidental leak | Low | Low | **Higher** | Low |
| Easy to explain on the call | Good | **Best** | Weakest | Good |
| Curl/README friendliness | Good | **Best** (OpenAPI docs) | Good | Good |

**✅ Decision: Option B (Python FastAPI + SQLite + vanilla JS).**

Things to get right because of this choice:
- Register a `RequestValidationError` handler that returns **400** with a readable message. FastAPI's default is 422.
- Write custom 401/403/404 handlers so every `/api` error is JSON: `{"error": "..."}`.
- The vanilla-JS router (History API, ~100 lines) handles: route matching incl. `/visits/:id`, query string ↔ filter
  form sync, `?next=` after login, the 404 page and the no-access page. The server returns `index.html` for every
  non-`/api` path so refresh works.
- Python deps kept minimal: `fastapi`, `uvicorn`, `pydantic` (bundled), with stdlib `sqlite3`, `csv`, `hashlib.scrypt`
  and `secrets`. `pandas` only for the throwaway Phase 0 audit. `pytest` + `httpx` (TestClient) for the leak test.

---

## 5. Architecture (stack-agnostic)

```
CSV files ──(startup loader: clean + normalise + dedupe)──▶ SQLite
                                                            │
  Browser ──▶ HTTP ──▶ [session middleware] ──▶ [role guard] ──▶ handler ──▶ role-specific SELECT ──▶ JSON
                         401 if none            403 if wrong role        400 on bad input
```

### Data model
- `allowed_users(email PK normalised, name, role)`: loaded from CSV and the **source of truth for role**
- `users(id, email UNIQUE normalised, password_hash, created_at)`: created by signup
- `sessions(token PK, user_email, created_at, expires_at)`
- `visits(...)`: cleaned columns, plus derived `local_date`, `dow`, `hour`, `duration_min NULL`, `signout_reliable BOOL`

Role is looked up from `allowed_users` **on every request**, not stored in the token, so removing someone
from the list cuts access immediately. **Fail closed:** a session whose email no longer has an `allowed_users` row
gets a 401, never a default role. Phase 2 must test this: remove someone from the CSV, restart, and their old
session gets 401. (From the Phase 1 review: accounts and sessions deliberately survive a reload.)

### The core security rule: projection by role, at the query
The viewer response is built from a **viewer-specific column allowlist**. Name/email columns are never
`SELECT`ed for a viewer in the first place. We don't fetch everything and delete keys afterwards.

| Field | Admin | Viewer |
|---|---|---|
| visit_id, date, signed in/out time, duration | ✅ | ✅ |
| visit_type, host_team, pre_registered | ✅ | ✅ |
| visitor_name, visitor_email | ✅ | ❌ absent |
| visitor_company | ✅ | ❌ absent (listed as admin-only in the brief) |
| host_name, host_email | ✅ | ❌ absent *(✅ decided: viewers see host team only)* |

Other leak routes we close:
- **Filters/sort:** viewers can't filter, search or sort by name/email/company. If they send that param they get a **400**, so ordering or match counts can't leak identity.
- **Detail endpoint:** `/api/visits/:id` uses the same projection.
- **Errors:** error messages never echo row data.
- **Stats:** only aggregate counts. *(Worth a line in the note: very small counts, e.g. "1 interview from team X on a day", could hint at identity. Out of scope, but we've thought about it.)*
- **Users list:** `/api/admin/users` returns **403** for viewers. The nav hiding the link is a courtesy; the API refusal is the real control.

### What a viewer sees where a name would be
**✅ Decision: nothing. For viewers, the visitor column doesn't exist.** A viewer cares about how busy it was, so
their table shows only: date, time in/out, length of visit, visit type, host team, pre-registered. No "Visitor"
placeholder, no dash, no initials (initials would leak identity in a 70-person office anyway).

The brief still requires the list and the single-visit page for viewers, so:
- The row itself is the link to `/visits/:id`. `visit_id` stays in the viewer payload only as a technical key for that
  link and isn't displayed as a label. It's a row number, not a person.
- The viewer's detail page is titled by the visit's shape, e.g. **"Interview on Tuesday 12 August at 10:14"**, not by a person.
- For the note to Dana: "Viewers don't see a stand-in for the visitor at all, because they never need one."

---

## 6. API (planned)

| Method & path | Who | Notes | Codes |
|---|---|---|---|
| `POST /auth/signup` `{email, password}` | anyone | normalised email must be on the list; one account per email | 201, 400, 403 (not on list), 409 (already signed up) |
| `POST /auth/login` `{email, password}` | anyone | sets cookie + returns `{token}` for curl | 200, 400, 401 (same message for wrong email *or* password) |
| `POST /auth/logout` | signed in | deletes session | 204, 401 |
| `GET /api/me` | signed in | `{email, name, role, can_see_identities}` | 200, 401 |
| `GET /api/visits?from=&to=&type=&page=&page_size=` | both | server-side filter + paging (default 50, max 200); role projection | 200, 400, 401 |
| `GET /api/visits/:id` | both | role projection | 200, 400 (bad id), 404, 401 |
| `GET /api/visits/types` | both | allowed visit types (drives the filter dropdown) | 200, 401 |
| `GET /api/stats?from=&to=&type=` | both | totals, by day-of-week, by hour, busiest day/hour, unreliable-period info | 200, 400, 401 |
| `GET /api/admin/users` | **admin** | allowed list + `signed_up: bool` | 200, 401, 403 |
| anything else under `/api` | — | JSON 404 | 404 |

Validation messages, written for humans:
`"End date (2025-07-01) is before start date (2025-08-01)."` ·
`"Unknown visit type 'intervew'. Choose one of: interview, delivery, …"` ·
`"Dates must look like 2025-08-14."`

**Signup refusal wording (✅ decided for now, may revisit):**
*"This email isn't on Brightline's access list. If you think it should be, ask Dana."* Reason: the app is internal,
the main users are colleagues who mistype, and a lockout with no explanation costs more than it protects. The
"enumeration" risk is small (8 people, and the attacker learns only that an email is on the list, still with no
account). The **login** error stays generic either way.

---

## 7. Pages (planned)

| Route | Who | Content |
|---|---|---|
| `/login`, `/signup` | anyone | forms, clear errors; after login → `?next=` target (only same-site paths, to avoid an open redirect) |
| `/visits` | both | headline numbers (total visits, busiest day of week, busiest hour, maybe a small by-hour table) + filters (from, to, type) **synced to the URL** + paged table |
| `/visits/:id` | both | admin: person + host + company; viewer: type, team, times, duration, with no visitor field at all |
| `/admin/users` | admin | allowed list, signed up yes/no; viewers get a clean "You don't have access to this page" (and no nav link) |
| `*` | anyone | real "Page not found" |

Client-side behaviour:
- On load, call `/api/me`. A 401 sends you to `/login?next=<current path+query>`.
- Every page fetch handles **loading / error / empty** with plain words ("No visits match these filters").
- An unreliable-data banner appears when the selected range overlaps the bad period.
- The server returns `index.html` for any non-`/api` path so refresh works on deep links (SPA fallback).

---

## 7b. UI design system

Goal: minimal, modern, consistent, and **not** the usual AI-generated look (shadcn card grids, cream + terracotta,
big-number stat tiles with gradients, ALL-CAPS eyebrow labels). Everything below lives in **one tokens file**, so
we can change the look later by editing tokens rather than hunting through pages.

### The subject, and where the look comes from
- **Subject:** a building lobby's sign-in log.
- **Audience:** Dana's workplace team, plus a few people who only need the busyness numbers.
- **Primary job:** answer *"when does the lobby get busy?"* at a glance, then let admins look up a specific visit.
- **Visual source:** building **wayfinding signage** and the **visitor badge**. Signage gives us very legible type,
  calm architectural colours, a strong left edge and generous space. The badge gives the single-visit page its shape.

### UI library: options for a no-build vanilla JS front end
| Option | Pros | Cons |
|---|---|---|
| **Web Awesome** (successor to Shoelace), web components ⭐ *recommended* | Real accessible components (inputs, select, date fields, button, alert/callout, badge, spinner, dialog) that work in plain HTML with no build step; fully themed through CSS custom properties, so it takes on **our** tokens instead of a stock look; MIT core; loads from a CDN or a vendored copy | Shadow DOM means some styling goes through `::part()`; heavier than a CSS-only kit; its default theme is recognisable unless we re-theme it (we will) |
| Shoelace 2.x | Same idea, very stable, lots of examples | Now in maintenance mode; Web Awesome is where new work goes |
| Pico CSS | Tiny, classless, near-zero effort | Instantly recognisable "Pico look"; few components; hard to make distinctive |
| Tailwind (standalone CLI, no Node) + Basecoat (shadcn-style HTML) | Modern utility workflow | That shadcn look is exactly the generic AI UI we want to avoid; adds a build step |
| Open Props (tokens only) + our own CSS | Total control, tiny | We hand-write every component, which costs time in a 3-hour box |

**Plan:** Web Awesome for form controls, buttons, callouts and spinners, re-themed with the tokens below. Data
tables and the heatmap are **plain semantic HTML + our CSS** because tables don't need a component, and that keeps
them fast and easy to explain. Pin an exact library version and vendor it into `static/vendor/` so the app works offline.

### Tokens
| Token | Value | Use |
|---|---|---|
| `--ground` | `#EEF1F0` limestone | page background (cool, not cream) |
| `--surface` | `#FFFFFF` | table, forms, badge |
| `--ink` | `#1E2B28` slate green | text, headings |
| `--ink-muted` | `#5D6B67` | secondary text, column headers |
| `--rule` | `#D3DAD7` | hairlines between table rows, input borders |
| `--signal` | `#0D6B5E` lobby green | primary buttons, links, focus ring, heatmap top step |
| `--heat-1…5` | `#E2EEEB` → `#0D6B5E` | 5-step single-hue heatmap ramp (accessible, colour-blind safe) |
| `--caution` | `#9A6A12` on `#FBF3E2` | the unreliable-data notice only |
| `--danger` | `#A23B2A` | form errors only |

- **Type:** one family, **Atkinson Hyperlegible Next** (designed for maximum legibility, which fits signage; not the
  default Inter), self-hosted in `static/fonts/`, falling back to the system UI font. Scale (1.25 ratio): 14 / 16
  (body) / 20 / 25 / 39. Tabular numerals in tables and the heatmap. Sentence case everywhere, no ALL-CAPS labels.
- **Shape:** small radius (6px) on inputs and buttons only. Tables and the page frame are square with hairline
  rules. No drop shadows except on a focused/open control. No gradients.
- **Spacing:** 4px base (4, 8, 12, 16, 24, 32, 48). Content max width ~1100px, **left-aligned** like a sign.
- **Motion:** none on load. Only small feedback motion (a button's loading state, a callout appearing). Respect `prefers-reduced-motion`.
- **Accessibility floor:** visible keyboard focus (2px `--signal` ring), AA contrast, labels on every input, the
  heatmap also readable as a table for screen readers.

### Layout per page
```
/visits  (the one bold element is the heatmap; everything else stays quiet)
┌──────────────────────────────────────────────────────────────┐
│ Front Desk        Visits   People with access*      Dana ▾  │  *admin only
├──────────────────────────────────────────────────────────────┤
│ The lobby is busiest on Tuesdays, around 10 am.             │  ← the answer, as a sentence (39px)
│ 1,987 visits from 1 Jun to 31 Aug.                          │
│                                                              │
│        7  8  9  10 11 12 13 14 15 16 17 18                  │
│  Mon   ░  ▒  ▓  ▓  ▒  ░  ▒  ▒  ░  ░  ·  ·                   │  ← day × hour heatmap
│  Tue   ░  ▒  ▓  █  ▓  ▒  ▒  ▒  ░  ░  ·  ·                   │
│  ...                                                         │
│                                                              │
│ ⚠ Sign-out times from 3 to 9 Jul weren't recorded, so visit │  ← only when the range overlaps
│   lengths for those days are left out.                      │
│                                                              │
│ From [ 2025-08-01 ]  To [ 2025-08-31 ]  Type [ Interview ▾ ] │  ← synced to the URL
│──────────────────────────────────────────────────────────────│
│ Date      In     Out    Length  Type       Team    Pre-reg  │  viewer columns
│ Tue 12 Aug 10:14 11:02  48 min  Interview  Design  Yes      │  (admin adds Visitor, Company, Host)
│ ...                                                Page 1/4 │
└──────────────────────────────────────────────────────────────┘

/visits/:id  (shaped like a visitor badge)
┌───────────────────────────┐
│ Interview                  │  viewer: the visit type is the title
│ Tuesday 12 August          │  admin: the visitor's name is the title,
│ 10:14 to 11:02 (48 min)    │         with email and company below
│ Hosted by the Design team  │  admin: "Hosted by Priya Shah (Design)"
│ Pre-registered             │
└───────────────────────────┘
← Back to visits (keeps your filters)

/login, /signup: a narrow, left-aligned form under the "Front Desk" wordmark. Errors appear inline under the field.
/admin/users: a plain table: name, email, role, signed up (Yes / Not yet).
404 / no access: one sentence that says what happened, plus one link to Visits.
```

### Copy rules
Plain words, sentence case, buttons say what they do ("Sign in", "Create account", "Apply filters"). No field names
on screen (no `signed_out_at`). Errors say what went wrong and how to fix it. Empty state: "No visits match these
filters. Try a wider date range."

### How we keep it consistent and changeable
- `static/css/tokens.css`: every colour, size, radius and spacing value, plus the Web Awesome theme mapping.
- `static/css/app.css`: layout and the few custom pieces (table, heatmap, badge), using **only** tokens.
- Before calling the UI done, take screenshots of every page as both admin and viewer and critique them against this section.
- Later restyling = edit `tokens.css`. Bigger changes = update this section first, then the code.

---

## 8. Build phases & time boxes (3h total)

| Phase | Time | Deliverable | Done when |
|---|---|---|---|
| **0. Data audit** | 0:00–0:15 | audit script + `DATA_NOTES.md` | both problems found, decision written for each |
| **1. Skeleton + loader** | 0:15–0:35 | repo, server boots, CSVs → cleaned SQLite, `README` stub | row counts after cleaning are printed and match the audit |
| **2. Auth** | 0:35–1:00 | signup (allowlist + normalise), login, logout, session middleware, `/api/me` | all 8 can sign up via curl; a stranger gets 403; no session gets 401 JSON |
| **3. Data endpoints** | 1:00–1:40 | `/api/visits`, `/api/visits/:id`, `/api/stats`, `/api/admin/users`, validation | **leak test passes**: viewer curl output, grepped for every visitor name & email from the CSV, has 0 hits; bad range gives 400 |
| **4. Pages** | 1:40–2:30 | `tokens.css` + Web Awesome theme first, then shell + role-aware nav, guards, login/signup, list + filters-in-URL + heatmap, detail, admin users, 404 | refresh on every route, paste a filtered URL in a fresh tab, login redirect returns to target |
| **5. Break it** | 2:30–2:45 | run the section 2 checklist as viewer, admin, and logged-out | every box ticked |
| **6. Note + README** | 2:45–3:00 | README (run steps, 2 test logins, 2 curl examples, endpoint table), note to Dana | someone can run it from the README alone |

**If we run short, drop in this order (as the brief says):** `/admin/users` page → `/visits/:id` page. Never
drop the API roles. Say what was dropped in the note.

### Automated leak test (built in Phase 3, re-run in Phase 5)
A script that: logs in as the viewer → hits `/api/visits` (every page, no filters + a few filters), `/api/visits/:id`
for several ids, `/api/stats` → greps every response for **every** `visitor_name` and `visitor_email` in the
CSV (case-insensitive) → fails on any hit. Also asserts: no session gives 401 on every endpoint, viewer gets 403 on
`/api/admin/users`, a bad date range gives 400. This is the reviewers' 15-second test, automated.

---

## 9. Decisions

| # | Decision | Status |
|---|---|---|
| 1 | Tech stack | ✅ **Option B**: Python FastAPI + SQLite + vanilla JS |
| 2 | Signup refusal wording | ✅ Friendly for now: *"This email isn't on Brightline's access list. If you think it should be, ask Dana."* (may revisit) |
| 3 | What viewers see where a name would be | ✅ Nothing. No visitor column for viewers (section 5) |
| 4 | Host names for viewers | ✅ Hidden. Host team only |
| 5 | Questions to email "Dana" on day one | ⏳ After the audit: office time zone, any conflicting user row, whether the bad sign-out period is known |

## 10. What happens next
1. ~~Pick the stack and answer section 9.~~ Done.
2. When the CSVs arrive, we run Phase 0 and update this plan with the real findings.
3. We turn phases 1–6 into a step-by-step implementation plan (superpowers `writing-plans`) and build phase by phase, curling the API before any page exists.

## 11. Deliverables checklist
- [ ] Repo with app + API, started via one README command
- [ ] README: setup, 2 test logins (1 admin, 1 viewer), 2 curl examples, endpoint docs
- [ ] Note to Dana: data problems found, access decisions + why, what's fake (passwords in local SQLite, no HTTPS, no email verification, sessions in a local file), what we'd do with real data (SSO, encryption at rest, audit log of who viewed which names, retention policy, small-count suppression), what was dropped/next
- [ ] No real secrets in the repo
