# Security test brief: The Front Desk

**For an independent reviewer (human or agent) with no other context.** Everything you need is in this file and the
repository. Read it top to bottom once, then work through sections 7–9 and write your report as described in section 12.

---

## 1. Mission

Independently verify that The Front Desk enforces its access rules **on the server**, and find any way around them.
Above all, find any way a **viewer** can learn a visitor's (or host's) name, email or company. Report what you tried,
what held, and anything that didn't, with evidence.

Assume the authors may have missed something. Don't take the passing test suites as proof; they are a starting point.

## 2. What the app must guarantee

From the original brief (quoted):

1. *"Only emails in allowed_users.csv may sign up. Anyone else is refused clearly — not a crash, not a blank page, not a silent failure."*
2. *"Match an email the way a person would expect."* Case and stray spaces must not lock out a listed colleague.
3. Roles:
   - *admin "sees everything: visitor names, email addresses, the company they came from, who hosted them."*
   - *viewer "sees how busy the building is — counts, dates, host teams, visit types. Never a visitor's name or email."*
4. *"A viewer must not be able to reach a name by any route you leave open. Not by editing the URL, not through a filter, and not by opening the network tab. Hiding a column while the data is still in the response doesn't count."*
5. *"Nothing returns data without a valid session. An unauthenticated call gets a 401 — a JSON error, not a redirect to HTML."*
6. *"A viewer's response must not contain a name or email anywhere in the payload. Not hidden, not nulled under another key — absent."*
7. *"Filtering and counting happen server-side."*
8. *"Bad input gets a 400 with a message a human can act on … Never a 500, never an empty 200."*
9. *"A route guard is a courtesy for the user, not a security control. Hiding /admin/users from the nav while your API will still answer a viewer's request for it is exactly the gap we're looking for."*

Design decisions made on top of the brief (test these too):
- **Host names and emails are also hidden from viewers.** They see `host_team` only.
- **Visitor company is admin-only.**
- **Role is looked up from the access list on every request.** Someone removed from `data/allowed_users.csv` loses access at the next restart, even with a live session.
- **Every login failure gives the same message.** That covers a wrong password, an unknown email, and a listed email that hasn't signed up.
- **Sign-up deliberately tells a stranger the email isn't on the list.** It's a friendly refusal; see README "Decisions". This is intended, not a finding.

## 3. Requirements

- macOS or Linux, with `bash`, `curl` and `python3` ≥ 3.10
- Node.js ≥ 22, for the JS unit tests and the browser checks. Uses the built-in `WebSocket` and `node:test`; no npm packages.
- Google Chrome at `/Applications/Google Chrome.app` (macOS), or set `CHROME=/path/to/chrome`. Only needed for the browser checks.
- Internet access is optional. The pages load one UI library (Web Awesome) from jsDelivr; everything works without it, just less styled.

## 4. Setup from a fresh copy

From the project folder:
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                     # sanity: all pass
```

Servers for testing always use `scripts/browser_check/serve-fresh.sh`. It starts the app on **port 8765 with a
throwaway database** (`var/check.db`) in the background, so you never touch anyone's real data. Re-running it resets
the database, and `pkill -f frontdesk-check-server` stops it. Don't use port 8000; someone may be running the app there.
```bash
export BASE=http://127.0.0.1:8765
```
Run the suites in the order given in section 7: the browser suite needs a server where nobody has signed up yet.

## 5. Accounts

| Role | Email | Password | Notes |
|---|---|---|---|
| admin | `dana.whitfield@brightline.example` | `frontdesk-admin` | created by `create_test_accounts.py`, `security_check.sh` and the browser suite |
| viewer | `sam.ferreira@brightline.example` | `frontdesk-viewer` | created by the same scripts. **Use Sam for leak greps:** Sam's name is not in the visit data |
| viewer | `ruth.grant@brightline.example` | `frontdesk-test` | created by `security_check.sh` (S11) |

The other listed emails (in `data/allowed_users.csv`) can be signed up with any password of 8+ characters. Some
listed people share a name with a visitor (Kenji Tanaka, Ruth Grant, Marcus Vitale, Priya Raghunathan, Jonas Lindqvist),
so a grep while signed in as them will find their **own** name in `/api/me`. That is not a leak; data endpoints never
include the caller's name.

Getting a token by hand:
```bash
T_VIEWER=$(curl -s -X POST "$BASE/api/auth/login" -H 'content-type: application/json' \
  -d '{"email":"sam.ferreira@brightline.example","password":"frontdesk-viewer"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
T_ADMIN=$(curl -s -X POST "$BASE/api/auth/login" -H 'content-type: application/json' \
  -d '{"email":"dana.whitfield@brightline.example","password":"frontdesk-admin"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
```
Send as `-H "Authorization: Bearer $T_VIEWER"`. The browser uses the `fd_session` cookie instead. If both are sent,
the cookie wins.

## 6. Where things live

| Concern | File | What to look at |
|---|---|---|
| Role projection, the core rule | `app/visits.py` | `VIEWER_COLUMNS` / `ADMIN_COLUMNS` (lines 17–19), `columns_sql`, `row_to_item`, `list_visits`, `get_visit` |
| Session → user + role | `app/auth.py` | `resolve_session` (line 64): joins sessions → users → allowed_users; hashing; `SESSION_TTL` |
| Request auth | `app/deps.py` | `presented_token`, `current_user` (401), `require_admin` (403) |
| Filters and validation | `app/filters.py` | `parse_filters` (unknown parameter → 400), `parse_page`, `filters_sql` (bound parameters) |
| Endpoints | `app/routes/auth.py`, `visits.py`, `admin.py` | thin wrappers |
| Error format | `app/errors.py` | every error → `{"error": …}`; 500s never echo details |
| Page serving | `app/pages.py` | the shell for known paths, 404 for others, `/api/*` catch-all |
| CSV loading and cleaning | `app/loader.py` | email normalisation, duplicate removal, missing days |
| Frontend | `static/js/` | `dom.js` `h()` (text nodes only), `router.js` (guards), `lib/safe-next.js` (post-login redirect) |
| Full API spec | `docs/API.md` | |

## 7. Automated suites (run these first)

Run them **in this order**:

| # | Suite | Command | Expected last line |
|---|---|---|---|
| 1 | Python | `.venv/bin/python -m pytest -q` | `N passed` (no failures) |
| 2 | JavaScript | `node --test 'tests/js/*.test.mjs'` | `ℹ fail 0` |
| 3 | Real browser | `scripts/browser_check/serve-fresh.sh && node scripts/browser_check/run.mjs $BASE` | `52 passed, 0 failed` |
| 4 | curl security checks | `BASE=$BASE scripts/security_check.sh` (creates the test logins itself) | `30 passed, 0 failed` |

The browser suite signs Sam and Dana up as part of its checks, so **it must start on a fresh server** (step 3 restarts
it). On a server where they already exist, its `auth` scenario fails with a timeout. That's expected, not a finding.
For hand testing after step 4, the accounts in section 5 exist.

Things to know:
- `tests/test_leak.py` is the in-process version of the viewer sweep. It includes an admin control proving the sweep can see names.
- `scripts/security_check.sh` S27 does the same for curl.
- The authors also verified the checks can fail: in a scratch copy that leaked `visitor_name` to viewers, S3, S4 and S6 failed.

## 8. Test catalogue

### API (S1–S30, all automated in `scripts/security_check.sh`; read it for exact commands)

| ID | Try | Expected |
|---|---|---|
| S1 | Every data endpoint with no session | 401 JSON `{"error":"Sign in to continue."}`, `content-type: application/json`, no redirect |
| S2 | `Bearer nonsense`, `Basic abc`, bare `Bearer`, cookie `fd_session=garbage` | 401 |
| S3 | Viewer: every page of `/api/visits?page_size=200`, searched for every visitor name, visitor email, company, host name and host email in the CSV | 0 found |
| S4 | Viewer: `/api/visits/:id` for ~50 ids across the file | 0 found; no `"visitor"` or `"host"` key |
| S5 | Viewer: `/api/stats` (all, `?type=interview`, August) | 0 found |
| S6 | Same request, viewer vs admin, item keys | viewer: `date,duration_min,host_team,pre_registered,signed_in,signed_out,visit_id,visit_type`; admin adds `host,visitor` |
| S7 | Viewer `?visitor_name=`, `?q=`, `?sort=visitor_name`, `?visitor_email=`, `?host_name=`, `?company=` | 400 `Unknown filter: …` |
| S8 | Viewer `GET /api/admin/users` | 403 `You don't have access to this.`, no names in the body |
| S9 | Admin `GET /api/admin/users` | 200, 8 people |
| S10 | Sign-up with an email not on the list | 403, the agreed refusal message |
| S11 | Sign-up `" Ruth.Grant@BRIGHTLINE.example "` | 201 (409 on re-run), then login as `ruth.grant@brightline.example` works |
| S12 | Sign up an existing account | 409 |
| S13 | Login: wrong password / unknown email / listed but not signed up | identical 401 `Email or password is incorrect.` |
| S14 | Login `Set-Cookie` | `HttpOnly`, `SameSite=lax`, `Max-Age=28800`, `Path=/` |
| S15 | Logout, then reuse the token | logout 204, then 401 |
| S16 | Bad dates, end before start, unknown type, page 0 / 999 / 5000 digits, page_size 500, repeated `type` | 400 with the exact messages in `docs/API.md` |
| S17 | `' OR 1=1--`, `1;DROP TABLE visits`, a `UNION SELECT` in `type`, `from` and the id | 400/404; `/api/stats` total still 1953 |
| S18 | Non-JSON, empty and `[]` bodies to signup and login | 400 with a message |
| S19 | `{"email":"\ud800", …}` | 400 |
| S20 | `GET` and `POST /api/nope` | 404 JSON |
| S21 | `GET /no/such/page` | 404, HTML shell |
| S22 | `GET /visits` with no session | 200 shell containing no data |
| S23 | `/openapi.json`, `/docs` | 200, no visitor data (schema only; intentional) |
| S24 | Foreign `Origin` header | no `access-control-allow-origin` |
| S25 | Ids `%2e%2e`, 5,000 characters, `%00`, `V001912%2F..%2F..` | 404, never 500 |
| S26 | `V001996` (a removed duplicate) as viewer and admin | identical 404 |
| S27 | Control: the S3 search over an admin page | > 50 identities found |
| S28 | The HTML shell | `text/html`, no stack traces |
| S29 | `page_size=200` | ≤ 200 items |
| S30 | `/api/stats` as viewer vs admin | byte-identical |

### Browser (B1–B10; most are automated in `scripts/browser_check/run.mjs`, the rest are manual)

| ID | Try | Expected | How |
|---|---|---|---|
| B1 | Signed out, open `/visits` | sent to `/login?next=%2Fvisits`; after login, land on `/visits` | auto |
| B2 | `/login?next=` set to `//evil.example`, `https://evil.example`, `/\evil.example`, `/%09/evil.example`, `/%0A/evil.example`, `javascript:alert(1)` | after login you stay on this site (`/visits`) | partly auto; try the rest by hand |
| B3 | As viewer, the network tab: search all responses for `Sofia Reyes`, `Clara Haddad`, `Oakfield Legal` | no matches; as admin, matches | manual, see `docs/NETWORK_TAB_CHECK.md` (the `visits` scenario checks the viewer's raw `/api/visits` response has no `visitor`/`host` key) |
| B4 | As viewer, `/visits/V001912` | badge shows "Guest", "Hosted by the Finance team", no person; the response has no `visitor` key | auto |
| B5 | As viewer, `/admin/users` | "You don't have access to this page"; no nav link; `fetch('/api/admin/users')` → 403 | auto |
| B6 | Refresh on every page incl. `/visits/V001912` and `/visits?…&page=3` | same page, still signed in | auto |
| B7 | A pasted filtered link in a fresh tab | opens filtered | auto |
| B8 | Data rendered as HTML? All rendering goes through `static/js/dom.js` `h()` (text nodes only) | no `innerHTML` with data anywhere: `grep -rn "innerHTML\|insertAdjacentHTML\|outerHTML" static/js` is empty | manual + unit test |
| B9 | Bad URLs: `/visits?from=2026-08-31&to=2026-08-01`, `/visits/%E0%A4%A`, `/whatever` | the API's 400 message / "Page not found" / "Page not found"; never blank | auto |
| B10 | Sign out as admin, sign in as viewer in the same tab, press Back to a visit the admin opened | refetched; no name shown | manual |

## 9. Worth probing beyond the catalogue

- **Side channels for identity:** ordering, counts or timing that differ by a visitor's name. Can any combination of `from`/`to`/`type` plus the stats single out a person? (Small counts are a known limit; see section 10.)
- **Session handling:** expiry (8 h; `SESSION_TTL` in `app/auth.py`), logout, and what happens when a listed person is removed from `data/allowed_users.csv` and the server restarts. Their old token should get 401.
- **Header and encoding tricks:** duplicate `Authorization` headers, mixed-case `bearer`, unicode in emails, very large bodies.
- **The page catch-all** (`app/pages.py`): can any path reach a file outside `static/`, or bypass `/api` routing?
- **`/docs` and `/openapi.json`** are public by design. Confirm they expose nothing beyond the API's shape.
- **Anything in `static/js` that trusts the client:** the route guard should never be the only thing protecting data.

## 10. Out of scope by design (don't report these as findings)

These come from the brief ("Not needed — skip it") or are documented decisions:
- No rate limiting, HTTPS, password reset, 2FA, SSO or email verification.
- CSRF beyond `SameSite=Lax` cookies.
- Sign-up says "isn't on the access list": the friendly refusal is deliberate (README "Decisions").
- `/docs` and `/openapi.json` being reachable without a session.
- **Small-count re-identification:** a viewer can see, for example, "one interview hosted by Legal on 3 Sep". This is noted in `docs/NOTE_TO_DANA.md` as future work.
- **Known minor issues the authors deferred:**
  - a stale cookie wins over a valid Bearer header
  - login doesn't revoke the session it replaces
  - an 8-space password is accepted
  - a tab keeps showing the admin nav after another tab signs in as a viewer (the API still refuses)
  - the heatmap's hover readout can't be reached by keyboard

  Report these only if you find they have a worse effect than described.

## 11. Rules of engagement

- Test **only** against `localhost`.
- **Do not modify** anything in `app/`, `static/`, `data/`, `tests/` or `scripts/`. Put throwaway scripts in `/tmp`.
- Don't commit anything. Your only output in the repo is the report file below.
- Use the throwaway server from section 4. Never point tests at `var/frontdesk.db`.

## 12. Report

Write **`docs/SECURITY_FINDINGS.md`** with:

```markdown
# Security findings: The Front Desk
Date, reviewer, version (`git rev-parse --short HEAD`, or "zip copy" if there's no `.git`), environment (OS, Python, Node, Chrome versions)

## Summary
One paragraph: does the viewer/admin boundary hold? Count of findings by severity.

## Suite results
| Suite | Result line |

## Findings
| ID | Severity | Where (endpoint / page / file:line) | Steps to reproduce | Expected | Actual | Evidence |
Severity: Critical (a viewer or stranger can read identities, or anyone can get in) · High (access control bypass
without identities, or a crash reachable by any user) · Medium (a brief rule broken: 500 on bad input, blank page,
redirect instead of 401) · Low (hardening) · Info (observations)

## Tested and held
Every catalogue ID and anything extra you tried, one line each, with how you checked it.
```
