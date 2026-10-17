# Phase 4: Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The pages on top of the finished API: login, sign-up, visits (headline + day×hour heatmap + filters + table), single visit, people with access, a real 404 and a clean "no access" page. Every page has its own URL, survives refresh and opens filtered when pasted.

**Architecture:** FastAPI serves one `static/index.html` shell for every known page path (and the same shell with status 404 for unknown paths). A small vanilla-JS app (native ES modules, no build step) routes with the History API, asks `/api/me` who you are, and renders pages with DOM methods. Pure logic (URL ↔ filters, route matching, formatting, safe redirects) lives in `static/js/lib/` and is unit-tested with `node --test`. Styling: Web Awesome 3.14.0 from jsDelivr (its theme and `native.css` style plain HTML forms and tables; two components, `wa-callout` and `wa-spinner`), re-themed by our `static/css/tokens.css`. Atkinson Hyperlegible Next is self-hosted.

**Tech Stack:** FastAPI `StaticFiles`, vanilla JS (ES modules), Web Awesome 3.14.0 (MIT, CDN, pinned), Node 23 `node:test` for JS unit tests.

**Spec:** `docs/plan.md` sections 2 (Pages), 7 (pages table, client behaviour), **7b (UI design system: tokens, layout, copy rules)**, 9 (decisions). `docs/DATA_NOTES.md` V2–V5 for the wording of the data notices.

## Global Constraints

- **Security:** never put API data into `innerHTML`. Build DOM with a helper `h(tag, attrs, ...children)` that sets text via `textContent`. Visitor names come from a CSV and are untrusted.
- **The API is the security control. Route guards are a courtesy.** A viewer is shown the no-access page for `/admin/users`, and the nav never shows them that link. The page never relies on the guard for safety.
- **URLs:** pages `/login`, `/signup`, `/visits`, `/visits/:id`, `/admin/users`; `/` redirects to `/visits`. Filters live in the query string with the API's names: `/visits?from=2026-08-01&to=2026-08-31&type=interview&page=2`. The page reads its state **only** from the URL.
- **Not signed in** → `/login?next=<path+query>`. After login → `next` if it's a safe same-site path (starts with `/`, not `//`, not `/\`), else `/visits`.
- **Nothing data-specific in code:** visit types come from `/api/visit-types`, hours and weekdays from `/api/stats`, missing days from `/api/stats.missing_days`.
- **Web Awesome:** pinned `3.14.0` from `https://cdn.jsdelivr.net/npm/@awesome.me/webawesome@3.14.0/dist-cdn/` (`styles/webawesome.css` + `webawesome.loader.js`). Only `wa-callout` and `wa-spinner` are used as components. Forms, buttons and tables are native elements styled by WA's `native.css`, so the app still works if the CDN is unreachable.
- **Design (docs/plan.md 7b):**
  - Tokens: `--ground #EEF1F0`, `--surface #FFFFFF`, `--ink #1E2B28`, `--ink-muted #5D6B67`, `--rule #D3DAD7`, `--signal #0D6B5E`, `--heat-1…5 #E2EEEB → #0D6B5E`, `--caution #9A6A12` on `#FBF3E2`, `--danger #A23B2A`.
  - Map onto WA: `--wa-color-brand-50: var(--signal)`, `--wa-color-brand-fill-loud: var(--signal)`, `--wa-font-family-body/heading: "Atkinson Hyperlegible Next", system-ui, sans-serif`, `--wa-border-radius-m: 6px`, `--wa-color-surface-default: var(--surface)`, `--wa-color-text-normal: var(--ink)`, `--wa-color-text-quiet: var(--ink-muted)`, `--wa-color-surface-border: var(--rule)`.
  - Light only. Type scale 14/16/20/25/39 px. Left-aligned, content max-width 1100px. No shadows, no gradients, no all-caps labels, sentence case, no load animations, visible 2px `--signal` focus ring, `prefers-reduced-motion` respected.
- **Copy:** plain words, no field names on screen.
  - A missing sign-out shows as "Didn't sign out".
  - Lengths read "1 h 19 min" or "48 min".
  - Dates on screen read "Tue 12 Aug 2026"; the detail page title reads "Tuesday 12 August 2026".
  - Hours read "9 am", "12 pm", "3 pm".
  - Button labels: "Sign in", "Create account", "Apply filters", "Clear filters", "Sign out", "Previous", "Next".
- No new Python dependencies. No npm packages: JS tests use only `node:test` and `node:assert`.

## Review Focus

1. **Refresh on `/visits/V001912?` or a filtered `/visits?…&page=3`** must land on the same page, still signed in. Test via the server-route tests (Task 1) and the browser pass (Task 6).
2. **A pasted link with a bad filter** (e.g. `?to=` before `?from=`, or `?type=nope`) must show the API's own 400 message in the page, not a blank table or a crash. Task 4, browser pass.
3. **A `next=` pointing off-site** (`//evil.example`, `https://evil.example`, `/\evil.example`) must be ignored after login. Unit test in Task 2.
4. **A visitor name containing HTML** (`<img src=x onerror=alert(1)>`) must show as text. Unit test of `h()` in Task 2.
5. **The 10–13 Aug gap inside a filtered range** must show the plain notice. A range with no visits must show the empty state, not "busiest on ." Task 4 (`headline()` unit test) and browser pass.

---

## File Structure

```
app/pages.py                 page routes: shell for known paths, 404 shell otherwise, / → /visits, /static mount
static/index.html            the shell: head (fonts, WA css+loader, our css), <header id="nav">, <main id="app">
static/css/tokens.css        every colour/size/space/radius + the WA variable mapping
static/css/app.css           layout + custom pieces (nav, table, heatmap, badge, notices), tokens only
static/fonts/                AtkinsonHyperlegibleNext-latin.woff2, -latin-ext.woff2, OFL.txt
static/js/main.js            boot: load /api/me, start router
static/js/router.js          History API: link interception, popstate, render by route, guards
static/js/api.js             fetch wrapper: JSON, cookie session, 401 → login redirect, ApiError(message,status)
static/js/dom.js             h(), clear(), the only DOM-building helpers
static/js/lib/routes.js      matchRoute(path) → {name, params} | null; ROUTES with access: "public"|"user"|"admin"
static/js/lib/urlstate.js    filtersFromSearch(search) / searchFromFilters(filters)
static/js/lib/format.js      fmtDate, fmtLongDate, fmtTime, fmtDuration, fmtHour, fmtCount, joinWords, dayRanges
static/js/lib/safe-next.js   safeNext(raw) → path
static/js/lib/headline.js    headline(stats) → {title, subtitle}; gapNotice(missing_days) → string | null
static/js/pages/login.js, signup.js, visits.js, visit.js, users.js, notfound.js, noaccess.js
static/js/components/nav.js, heatmap.js, filters.js, table.js
tests/test_pages.py          server routing of pages
tests/js/*.test.mjs          node --test unit tests for lib/ and dom.js
```

---

### Task 1: Serve the shell for every page URL

**Files:**
- Create: `app/pages.py`, `static/index.html` (minimal shell for now), `tests/test_pages.py`
- Modify: `app/main.py` (register **after** the API routers), `app/errors.py` (non-`/api` 404s go to the shell)

**Interfaces:**
- Produces: `install_pages(app: FastAPI, static_dir: Path) -> None`. Known page patterns: `^/login$`, `^/signup$`, `^/visits$`, `^/visits/[^/]+$`, `^/admin/users$`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pages.py
def test_known_pages_serve_the_shell(client):
    for path in ("/login", "/signup", "/visits", "/visits?from=2026-08-01&type=interview", "/visits/V001912", "/admin/users"):
        r = client.get(path)
        assert r.status_code == 200 and '<main id="app"' in r.text, path


def test_root_redirects_to_visits(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/visits"


def test_unknown_page_is_a_real_404_with_the_shell(client):
    r = client.get("/no/such/page")
    assert r.status_code == 404 and '<main id="app"' in r.text


def test_api_404_is_still_json(client):
    assert client.get("/api/nope").json() == {"error": "No such endpoint: GET /api/nope"}


def test_static_files_are_served(client):
    assert client.get("/static/index.html").status_code == 200


def test_shell_needs_no_session_but_data_still_does(client):
    assert client.get("/admin/users").status_code == 200
    assert client.get("/api/admin/users").status_code == 401
```

- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_pages.py -q`. Expected: FAIL (404 JSON for `/login`).
- [ ] **Step 3: Implement.** Mount `StaticFiles` at `/static`. Add a `GET /` redirect. Add a catch-all `GET /{path:path}` (`include_in_schema=False`) returning `FileResponse(index.html)` with status 200 when a page pattern matches, else 404. API paths never reach it because the routers are registered first. Unmatched `/api/...` still hits the JSON 404 handler: make the catch-all raise `HTTPException(404)` for any path starting with `api/`.
- [ ] **Step 4: Run** `.venv/bin/python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: serve the page shell for every page URL; real 404 for unknown pages`

---

### Task 2: Pure JS logic, unit-tested with node

**Files:** create everything under `static/js/lib/`, `static/js/dom.js`, `tests/js/*.test.mjs`

**Interfaces (all ES module named exports):**
- `matchRoute(path: string) → {name, params, access} | null`. Names: `login, signup, visits, visit, users`. `visit` params `{id}` (URI-decoded). Access: login/signup `public`, visits/visit `user`, users `admin`.
- `filtersFromSearch(search: string) → {from, to, type, page}`. Missing → `""`; `page` → integer ≥ 1, default 1.
- `searchFromFilters(f) → string`. Leading `?`, omits empty values and `page=1`, order `from, to, type, page`. Returns `""` when empty.
- `safeNext(raw: string | null) → string`
- `fmtDate("2026-08-12") → "Wed 12 Aug 2026"`, `fmtLongDate → "Wednesday 12 August 2026"`, `fmtTime("2026-08-12 09:05:00") → "09:05"`, `fmtDuration(79) → "1 h 19 min"`, `fmtDuration(48) → "48 min"`, `fmtDuration(null) → "Didn't sign out"`, `fmtHour(9) → "9 am"`, `fmtHour(12) → "12 pm"`, `fmtHour(15) → "3 pm"`, `fmtCount(1953) → "1,953"`, `joinWords(["a","b","c"]) → "a, b and c"`
- `dayRanges(["2026-08-10","2026-08-11","2026-08-12","2026-08-13","2026-09-01"]) → [["2026-08-10","2026-08-13"],["2026-09-01","2026-09-01"]]` (consecutive calendar days merge)
- `headline(stats) → {title, subtitle}` and `gapNotice(missing_days) → string | null`
- `h(tag, attrs?, ...children) → Element` (strings become text nodes; `attrs` keys: `class`, `href`, `on<event>` functions, any other attribute via `setAttribute`); `clear(el)`

- [ ] **Step 1: Write the failing tests** (`tests/js/lib.test.mjs`, `tests/js/dom.test.mjs`). Exact cases:

```js
// tests/js/lib.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { matchRoute } from "../../static/js/lib/routes.js";
import { filtersFromSearch, searchFromFilters } from "../../static/js/lib/urlstate.js";
import { safeNext } from "../../static/js/lib/safe-next.js";
import * as f from "../../static/js/lib/format.js";
import { headline, gapNotice } from "../../static/js/lib/headline.js";

test("routes", () => {
  assert.deepEqual(matchRoute("/visits/V001912"), { name: "visit", params: { id: "V001912" }, access: "user" });
  assert.equal(matchRoute("/admin/users").access, "admin");
  assert.equal(matchRoute("/nope"), null);
  assert.equal(matchRoute("/visits/a/b"), null);
});

test("url state round-trips and drops defaults", () => {
  const s = "?from=2026-08-01&to=2026-08-31&type=interview&page=2";
  assert.deepEqual(filtersFromSearch(s), { from: "2026-08-01", to: "2026-08-31", type: "interview", page: 2 });
  assert.equal(searchFromFilters(filtersFromSearch(s)), s);
  assert.equal(searchFromFilters({ from: "", to: "", type: "", page: 1 }), "");
  assert.equal(filtersFromSearch("?page=abc").page, 1);
});

test("safeNext only allows same-site paths", () => {
  assert.equal(safeNext("/visits?type=guest"), "/visits?type=guest");
  for (const bad of ["//evil.example", "https://evil.example", "/\\evil.example", "javascript:alert(1)", "", null]) {
    assert.equal(safeNext(bad), "/visits", String(bad));
  }
});

test("formatting", () => {
  assert.equal(f.fmtDate("2026-08-12"), "Wed 12 Aug 2026");
  assert.equal(f.fmtLongDate("2026-08-12"), "Wednesday 12 August 2026");
  assert.equal(f.fmtTime("2026-08-12 09:05:00"), "09:05");
  assert.equal(f.fmtDuration(79), "1 h 19 min");
  assert.equal(f.fmtDuration(48), "48 min");
  assert.equal(f.fmtDuration(null), "Didn't sign out");
  assert.deepEqual([9, 12, 15].map(f.fmtHour), ["9 am", "12 pm", "3 pm"]);
  assert.equal(f.fmtCount(1953), "1,953");
  assert.equal(f.joinWords(["Tuesdays", "Wednesdays"]), "Tuesdays and Wednesdays");
  assert.deepEqual(f.dayRanges(["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-09-01"]),
    [["2026-08-10", "2026-08-13"], ["2026-09-01", "2026-09-01"]]);
});

const base = { total_visits: 1953, range: { from: "2026-07-01", to: "2026-09-30" },
  busiest_days: ["Tuesday", "Wednesday"], busiest_hours: [9], missing_days: [] };

test("headline", () => {
  assert.deepEqual(headline(base), {
    title: "The lobby is busiest on Tuesdays and Wednesdays, around 9 am.",
    subtitle: "1,953 visits from Wed 1 Jul 2026 to Wed 30 Sep 2026." });
  assert.equal(headline({ ...base, busiest_hours: [10, 11] }).title,
    "The lobby is busiest on Tuesdays and Wednesdays, around 10 am and 11 am.");
  assert.equal(headline({ ...base, total_visits: 0, busiest_days: [], busiest_hours: [] }).title, "No visits in this period.");
});

test("gap notice", () => {
  assert.equal(gapNotice([]), null);
  assert.equal(gapNotice(["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"]),
    "The lobby iPad recorded no sign-ins from Mon 10 Aug 2026 to Thu 13 Aug 2026, so totals that include those days are incomplete.");
});
```

```js
// tests/js/dom.test.mjs: h() with a tiny fake document (no jsdom)
import { test } from "node:test";
import assert from "node:assert/strict";
import { makeFakeDocument } from "./fake-dom.mjs";   // ~30-line stub: createElement, createTextNode, setAttribute, append, addEventListener
globalThis.document = makeFakeDocument();
const { h } = await import("../../static/js/dom.js");

test("h puts untrusted text in text nodes, never markup", () => {
  const el = h("td", {}, "<img src=x onerror=alert(1)>");
  assert.equal(el.children[0].nodeType, 3);
  assert.equal(el.children[0].textContent, "<img src=x onerror=alert(1)>");
});

test("h sets class, href and listeners", () => {
  let clicked = false;
  const a = h("a", { class: "row", href: "/visits/V1", onclick: () => { clicked = true; } }, "Open");
  assert.equal(a.attributes.class, "row");
  assert.equal(a.attributes.href, "/visits/V1");
  a.listeners.click();
  assert.equal(clicked, true);
});
```

- [ ] **Step 2: Run** `node --test tests/js/`. Expected: FAIL (`Cannot find module …/routes.js`).
- [ ] **Step 3: Implement** the modules. Format dates by splitting the ISO string and using fixed English day and month name arrays, never `new Date(string)` (that would apply time-zone shifts). Plural weekday = name + "s".
- [ ] **Step 4: Run** `node --test tests/js/`. Expected: all pass. Then `.venv/bin/python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: page logic (routes, URL state, safe redirects, formatting, headline) with node tests`

---

### Task 3: Design system, shell, nav, router, login/sign-up, 404 and no-access

**Files:** `static/index.html`, `static/css/tokens.css`, `static/css/app.css`, `static/fonts/*`, `static/js/main.js`, `router.js`, `api.js`, `components/nav.js`, `pages/login.js`, `signup.js`, `notfound.js`, `noaccess.js`

**Behaviour:**
- Fonts: download the two latin and latin-ext woff2 files listed by `https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:wght@400;700&display=swap` (fetched with a browser user agent) into `static/fonts/`, plus the OFL licence text. Declare them in `tokens.css` with `@font-face` and `font-display: swap`.
- `api.js`: `api(path, {method, body}) → data`. Uses `credentials: "same-origin"`. On a non-OK response it throws `ApiError(message from {"error"}, status)`. On a 401 from anything except `/api/auth/*` it navigates to `/login?next=<current path+query>`.
- Router: intercepts clicks on same-origin `<a>` (no modifier keys, no `target`, no `download`) and calls `history.pushState`; handles `popstate`; `navigate(url, {replace})`. For every render:
  1. `matchRoute`
  2. if null → not-found page (the server already sent status 404)
  3. if access is not public → ensure `/api/me` is loaded (cached until sign-in or sign-out); a 401 → `/login?next=…` (replace)
  4. admin route and `role !== "admin"` → no-access page
  5. render
  - It sets `document.title` to `"<Page> · Front Desk"` and moves focus to the page's `<h1>`.
- Nav (shown when signed in): wordmark "Front Desk" (link to `/visits`), "Visits", "People with access" (**admins only**), then on the right the user's name, their role in muted text ("viewer" or "admin"), and a "Sign out" button. Sign out calls `POST /api/auth/logout`, clears the `me` cache and goes to `/login`.
- Login: an email and password form plus a "Sign in" button. Errors show inline under the form in `wa-callout variant="danger"` with the API's message. On success it navigates to `safeNext(next)`. Below the form: "New here? Create an account" → `/signup?next=…`.
- Sign-up: same layout with "Create account". On 201 it logs in with the same credentials and goes to `next`. The 403 shows the agreed refusal message verbatim from the API.
- Not found: an `<h1>` "Page not found", one sentence "There's nothing at <path>.", and a link "Go to visits".
- No access: an `<h1>` "You don't have access to this page", "Only admins can see who has access to the app.", and a link "Go to visits".
- Loading states use `wa-spinner` with visible text ("Loading…"), never a blank screen.

- [ ] **Step 1:** Add the fonts and write `tokens.css` and `app.css` from Global Constraints. Write `index.html`: `<html lang="en" class="wa-light">`, WA css + loader `<script type="module">`, our CSS **after** WA's, `<header id="nav">`, `<main id="app" tabindex="-1">`, `<script type="module" src="/static/js/main.js">`. Use absolute `/static/...` paths, so deep URLs like `/visits/V1` load assets correctly.
- [ ] **Step 2:** Implement `api.js`, `router.js`, `main.js`, the nav, and the four pages.
- [ ] **Step 3: Verify in a browser** (server on port 8765). Each of these must hold:
  - `/visits` signed out → `/login?next=%2Fvisits`; sign up as Sam; you land on `/visits`.
  - `/admin/users` as Sam → no-access page, and the nav shows no "People with access".
  - `/whatever` → the not-found page.
  - Refresh on `/login?next=/visits%3Ftype%3Dguest`, then sign in → `/visits?type=guest`.
  - The browser console has no errors.
- [ ] **Step 4:** `node --test tests/js/ && .venv/bin/python -m pytest -q` → all pass.
- [ ] **Step 5: Commit** `feat: app shell, design tokens, router with guards, login, sign-up, 404 and no-access pages`

---

### Task 4: The visits page

**Files:** `static/js/pages/visits.js`, `components/filters.js`, `components/heatmap.js`, `components/table.js`; modify `app/visits.py` + `tests/test_stats_api.py` (add `by_weekday_hour`)

**API addition (TDD in Python first):** `compute_stats` gains `by_weekday_hour: [{weekday, hour, visits, avg_per_day}]`. It has one entry for every (weekday in `by_weekday`) × (hour in `by_hour`), and `avg_per_day = round(visits / operating_days of that weekday, 1)`. It is aggregates only, so it's identical for both roles, and the leak sweep already covers `/api/stats`.

```python
def test_weekday_hour_grid(client, viewer):
    s = stats(client, viewer)
    grid = {(c["weekday"], c["hour"]): c for c in s["by_weekday_hour"]}
    assert len(grid) == 5 * 7
    assert sum(c["visits"] for c in s["by_weekday_hour"]) == 1953
    assert grid[(1, 9)]["avg_per_day"] == max(c["avg_per_day"] for c in s["by_weekday_hour"])   # Tuesday 9 am is the hottest cell
    assert all(c["visits"] == 0 for c in s["by_weekday_hour"] if c["hour"] == 12)
```

**Page layout, top to bottom** (docs/plan.md 7b wireframe):
1. **Headline** `<h1>` from `headline(stats).title` (39px), with the subtitle below it.
2. **Heatmap:** rows = weekdays in `by_weekday`, columns = hours in `by_hour`, header labels from `fmtHour`. Each cell's shade comes from `--heat-1..5`, using quintiles of the non-zero `avg_per_day` values, with 0 as `--ground` plus a hairline. Each cell has `title` and `aria-label` text "Tuesday 9 am: 15.9 visits a day on average". It's a real `<table>` with a `<caption>` "Average sign-ins per day, by weekday and hour", so it reads as a table to screen readers.
3. **Visit length line:** "Median visit: 1 h 19 min, based on the 1,083 visits where the guest signed out." (counts from `visit_length`). It's omitted when `measured_visits` is 0.
4. **Gap notice:** `wa-callout variant="warning"` with `gapNotice(missing_days)`, only when non-null.
5. **Filters form:**
   - native `<input type="date">` "From" and "To", plus a `<select>` "Visit type" ("All types" + `/api/visit-types`)
   - "Apply filters" submits and pushes the new URL (page reset to 1)
   - "Clear filters" is a link to `/visits`
   - form values are always filled from the URL
6. **Table:**
   - Viewer columns: Date, Signed in, Signed out, Length, Type, Team, Pre-registered. Admin columns: Date, Visitor, Company, Host, Signed in, Signed out, Length, Type, Team.
   - The Date cell is the link to `/visits/:id`.
   - Visit type is shown capitalised ("Interview").
   - Pre-registered shows "Yes" or "No".
   - "Signed out" shows "Didn't sign out" when null.
7. **Pager:** "Showing 51–100 of 1,953", with "Previous" and "Next" links (hrefs built with `searchFromFilters`, disabled at the ends).

**States:**
- **Loading:** a spinner and "Loading visits…".
- **API 400** (from a pasted bad URL): `wa-callout variant="danger"` with the message, plus the filters form, so it can be fixed.
- **Empty:** "No visits match these filters. Try a wider date range." The heatmap is hidden and the headline says "No visits in this period."
- **Stats and the list load in parallel** (`Promise.all`) with the same filter query (minus `page` for stats).

- [ ] **Step 1:** Write the `by_weekday_hour` test. Run it and check it fails (`KeyError`). Implement it with one `GROUP BY weekday, hour` query. Run `pytest` and check it passes.
- [ ] **Step 2:** Implement the page and its components.
- [ ] **Step 3: Verify in a browser** as Sam, then as Dana (sign up Dana). Each of these must hold:
  - The headline reads "The lobby is busiest on Tuesdays and Wednesdays, around 9 am.", and the heatmap's darkest cell is Tue 9 am.
  - Applying From 2026-08-01, To 2026-08-31, type Interview changes the URL to `/visits?from=2026-08-01&to=2026-08-31&type=interview` and shows 115 visits with the gap notice. Copy that URL into a new tab and it opens filtered.
  - Refresh on page 3 keeps you on page 3. Back and Forward step through filter changes.
  - `/visits?from=2026-08-31&to=2026-08-01` shows the API's end-before-start message.
  - `/visits?from=2026-08-10&to=2026-08-13` shows the empty state and the gap notice.
  - Sam's table has no Visitor, Company or Host column. In DevTools Network, the `/api/visits` response has no names. Dana's table shows names.
  - The page is usable at 400px wide: the table scrolls horizontally inside its own container.
- [ ] **Step 4:** `node --test tests/js/ && .venv/bin/python -m pytest -q` → all pass.
- [ ] **Step 5: Commit** `feat: visits page with headline, weekday x hour heatmap, URL filters, role-aware table`

---

### Task 5: Single-visit page and people-with-access page

**Files:** `static/js/pages/visit.js`, `static/js/pages/users.js`

- **Single visit** (badge layout, docs/plan.md 7b):
  - **Viewer:** the title is the visit type ("Interview"), then the long date, "09:05 to 10:20 (1 h 15 min)" or "Signed in at 09:05, didn't sign out", "Hosted by the Design team", and "Pre-registered" / "Not pre-registered".
  - **Admin:** the title is the visitor's name, with email and company below it, and "Hosted by Nadia Ferreira (Finance)".
  - "Back to visits" returns to the last list URL, which the visits page stores in `sessionStorage` under `fd:lastList`; the fallback is `/visits`.
  - A 404 from the API → "No visit with id V001996. It may have been a duplicate sign-in that was removed." plus "Back to visits".
- **People with access** (admin): `<h1>` "People with access", the sentence "<n> people are on the access list. <k> have created an account." (counts from the API), and a table with Name, Email, Role, Signed up ("Yes" / "Not yet").
- [ ] **Step 1:** Implement both pages.
- [ ] **Step 2: Verify in a browser:**
  - Open a visit from the list, refresh it, and press Back: you return to the filtered list.
  - As Sam, `/visits/V001912` shows no name. In DevTools, the `/api/visits/V001912` response has no `visitor` key.
  - `/visits/V001996` shows the friendly 404.
  - As Dana, `/admin/users` lists 8 people, with Sam and Dana signed up.
  - As Sam, `/admin/users` shows the no-access page, and calling `/api/admin/users` from the browser console returns 403.
- [ ] **Step 3:** All tests pass. **Commit** `feat: single-visit badge page and people-with-access page`

---

### Task 6: Break it, then critique the design

- [ ] **Step 1: Brief checklist (docs/plan.md section 2, Pages)**, run in the browser and recorded in the ledger:
  - refresh on every page, including a single visit
  - a filtered link pasted into a fresh tab
  - signed out → login → back to the original page
  - a viewer typing `/admin/users`
  - every loading, empty and error state worded plainly
  - no `signed_out_at` or other field name anywhere on screen
- [ ] **Step 2: Screenshots** of every page as viewer and as admin at 1280px, plus `/visits` at 400px. Critique them against docs/plan.md 7b and the frontend-design checklist:
  - Does anything read as a generic AI template?
  - Is the heatmap the single bold element?
  - Is the type scale consistent?
  - Is the focus ring visible?

  Fix what fails, styling through tokens only.
- [ ] **Step 3:** All tests pass. **Commit** `polish: fixes from the browser pass and design critique`

---

## Phase 4 done when
- `node --test tests/js/` and `.venv/bin/python -m pytest -q` both pass.
- Every item in docs/plan.md section 2, "Pages", holds in a real browser.
- Viewer pages never show (and their API responses never contain) a visitor or host identity.
- `grep -rnE "2026|guest|interview|Engineering|Brightline" static/js` matches nothing except tests.
