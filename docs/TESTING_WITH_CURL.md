# Testing the access rules with curl

This walks through the checks by hand, so you can see for yourself that **a viewer's response never contains a
visitor's name, email or company**, along with the other access rules. Every command can be copied and pasted as is.
To run all of it in one go, use `scripts/security_check.sh` (last section).

You need `curl` and `python3`, both preinstalled on macOS and most Linux systems. No `jq` is needed.

---

## 1. Start the app and create the test logins

In one terminal, from the project folder:
```bash
.venv/bin/uvicorn app.main:app
```

In a second terminal, from the project folder:
```bash
export BASE=http://127.0.0.1:8000
.venv/bin/python scripts/create_test_accounts.py --base "$BASE"
```
You should see `Created admin login …` and `Created viewer login …` (or `Already exists: …` on a re-run).

| Role | Email | Password |
|---|---|---|
| admin | `dana.whitfield@brightline.example` | `frontdesk-admin` |
| viewer | `sam.ferreira@brightline.example` | `frontdesk-viewer` |

> **Why the viewer is Sam.** Several people on the access list share a name with a visitor in the data (Kenji Tanaka,
> Ruth Grant, Marcus Vitale and others). Sam Ferreira doesn't. If you grep a viewer's responses for visitor names
> while signed in as, say, Kenji, `/api/me` would contain "Kenji Tanaka" and look like a leak. The data endpoints
> never contain your own name, but a careless grep over everything would trip on it.

## 2. Log in (the brief's first example)

```bash
T_VIEWER=$(curl -s -X POST "$BASE/api/auth/login" -H 'content-type: application/json' \
  -d '{"email":"sam.ferreira@brightline.example","password":"frontdesk-viewer"}' \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["token"])')
T_ADMIN=$(curl -s -X POST "$BASE/api/auth/login" -H 'content-type: application/json' \
  -d '{"email":"dana.whitfield@brightline.example","password":"frontdesk-admin"}' \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["token"])')
echo "viewer token ${T_VIEWER:0:10}…  admin token ${T_ADMIN:0:10}…"
```
**You should see** two short token prefixes. The full login response looks like
`{"token": "…", "user": {"email": "sam.ferreira@brightline.example", "name": "Sam Ferreira", "role": "viewer"}}`.
The same token is also set as an `HttpOnly` cookie for the browser. With curl, send it as a Bearer header.

```bash
curl -s "$BASE/api/me" -H "Authorization: Bearer $T_VIEWER"; echo
```
**You should see** `"role":"viewer","can_see_identities":false`.

## 3. A filtered visits call (the brief's second example)

Guests on 30 September, newest first, one per page:
```bash
curl -s "$BASE/api/visits?type=guest&from=2026-09-30&to=2026-09-30&page_size=1" \
  -H "Authorization: Bearer $T_VIEWER" | python3 -m json.tool
```
**You should see** one item with `visit_id`, `date`, `signed_in`, `signed_out`, `duration_min`, `visit_type`,
`host_team` and `pre_registered`, plus `"total": 16`. There is **no `visitor` and no `host` key**.

The same call as the admin:
```bash
curl -s "$BASE/api/visits?type=guest&from=2026-09-30&to=2026-09-30&page_size=1" \
  -H "Authorization: Bearer $T_ADMIN" | python3 -m json.tool
```
**You should see** the same item plus `"visitor": {"name": "Sofia Reyes", …}` and `"host": {"name": "Nadia Ferreira", …}`.

## 4. Viewer vs admin, field by field

```bash
for who in viewer admin; do
  T=$T_VIEWER; [ "$who" = admin ] && T=$T_ADMIN
  printf '%-7s ' "$who"
  curl -s "$BASE/api/visits?page_size=1" -H "Authorization: Bearer $T" \
    | python3 -c 'import sys, json; print(", ".join(sorted(json.load(sys.stdin)["items"][0])))'
done
```
**You should see**
```
viewer  date, duration_min, host_team, pre_registered, signed_in, signed_out, visit_id, visit_type
admin   date, duration_min, host, host_team, pre_registered, signed_in, signed_out, visit_id, visit_type, visitor
```
The viewer's fields aren't hidden or nulled. The server never reads them from the database for a viewer
(`app/visits.py`, `VIEWER_COLUMNS`).

## 5. The reviewers' 15-second test

Log in as the viewer, call the visits endpoint, and search the raw response for a visitor's name:
```bash
curl -s "$BASE/api/visits?page_size=200" -H "Authorization: Bearer $T_VIEWER" | grep -ci "sofia reyes"
curl -s "$BASE/api/visits?page_size=200" -H "Authorization: Bearer $T_ADMIN"  | grep -ci "sofia reyes"
```
**You should see** `0` for the viewer and `1` for the admin. The admin line proves the name is in that page, so the 0 means something.

## 6. The full leak check: every name, every page

One name isn't proof. This takes **every** visitor name, visitor email, company, host name and host email from the
CSV (about 2,750 strings) and searches **all** pages of the viewer's visits for any of them:
```bash
IDS=$(mktemp); ALL=$(mktemp)
python3 -c '
import csv
rows = list(csv.DictReader(open("data/visits.csv", newline="")))
cols = ("visitor_name", "visitor_email", "visitor_company", "host_name", "host_email")
print("\n".join(sorted({r[c].strip() for r in rows for c in cols})))' > "$IDS"
echo "identities to look for: $(wc -l < "$IDS")"
for p in $(seq 1 10); do
  curl -s "$BASE/api/visits?page=$p&page_size=200" -H "Authorization: Bearer $T_VIEWER"; echo
done > "$ALL"
echo "visits in the viewer's responses: $(grep -o '"visit_id"' "$ALL" | wc -l)"
echo "pages containing any identity:   $(grep -ciF -f "$IDS" "$ALL")"
```
**You should see** about 2,750 identities, 1,953 visits, and **`pages containing any identity: 0`**.

The control: run the same search over the admin's first page, which should find plenty.
```bash
curl -s "$BASE/api/visits?page_size=200" -H "Authorization: Bearer $T_ADMIN" \
  | python3 -c 'import sys; page = sys.stdin.read().lower(); print(sum(i.lower() in page for i in open(sys.argv[1]).read().splitlines() if i))' "$IDS"
rm -f "$IDS" "$ALL"
```
**You should see** about 500: the names, emails, companies and hosts on one page of 200 visits.

## 7. One visit, and the stats

```bash
curl -s "$BASE/api/visits/V001912" -H "Authorization: Bearer $T_VIEWER"; echo
curl -s "$BASE/api/visits/V001912" -H "Authorization: Bearer $T_ADMIN"; echo
curl -s "$BASE/api/stats?from=2026-08-01&to=2026-08-31&type=interview" -H "Authorization: Bearer $T_VIEWER" \
  | python3 -c 'import sys, json; d = json.load(sys.stdin); print(d["total_visits"], d["busiest_days"], d["busiest_hours"], d["missing_days"])'
```
**You should see**
- the viewer's visit with no `visitor` or `host`
- the admin's visit with them
- `115 ['Wednesday'] [9] ['2026-08-10', '2026-08-11', '2026-08-12', '2026-08-13']`

Stats are counts only, and the same for both roles.

## 8. What the API refuses

```bash
# A viewer asking for the admin list: 403, whatever any page shows
curl -s -w '  [%{http_code}]\n' "$BASE/api/admin/users" -H "Authorization: Bearer $T_VIEWER"

# No session: a JSON 401, never a redirect to a login page
curl -s -i "$BASE/api/visits" | grep -iE '^HTTP|^content-type|error'

# Trying to filter or sort by identity: 400
curl -s -w '  [%{http_code}]\n' "$BASE/api/visits?visitor_name=Sofia" -H "Authorization: Bearer $T_VIEWER"

# Someone not on the access list: refused clearly
curl -s -w '  [%{http_code}]\n' -X POST "$BASE/api/auth/signup" -H 'content-type: application/json' \
  -d '{"email":"stranger@example.com","password":"whatever123"}'
```
**You should see**
- `{"error":"You don't have access to this."}  [403]`
- `HTTP/1.1 401 Unauthorized`, `content-type: application/json` and `{"error":"Sign in to continue."}`
- `{"error":"Unknown filter: visitor_name. Use from, to, type, page, page_size."}  [400]`
- `{"error":"This email isn't on Brightline's access list. If you think it should be, ask Dana."}  [403]`

## 9. Bad input gets a 400 a person can act on

```bash
for q in "from=2026-08-31&to=2026-08-01" "type=intervew" "from=14/08/2026" "page=999" "page_size=500"; do
  curl -s -w '  [%{http_code}]\n' "$BASE/api/visits?$q" -H "Authorization: Bearer $T_VIEWER"
done
```
**You should see** five `[400]` lines:
- `The end date (2026-08-01) is before the start date (2026-08-31).`
- `Unknown visit type 'intervew'. Choose one of: contractor, guest, interview, vendor.`
- `from must be a date written as YYYY-MM-DD.`
- `Page 999 doesn't exist. There are 40 pages.`
- `page_size must be a whole number from 1 to 200.`

## 10. Logging out ends the session

```bash
T_SPARE=$(curl -s -X POST "$BASE/api/auth/login" -H 'content-type: application/json' \
  -d '{"email":"sam.ferreira@brightline.example","password":"frontdesk-viewer"}' \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["token"])')
curl -s -o /dev/null -w 'logout   [%{http_code}]\n' -X POST "$BASE/api/auth/logout" -H "Authorization: Bearer $T_SPARE"
curl -s -o /dev/null -w 'after    [%{http_code}]\n' "$BASE/api/me" -H "Authorization: Bearer $T_SPARE"
```
**You should see** `logout [204]` then `after [401]`.

## 11. All of it at once

```bash
BASE=$BASE scripts/security_check.sh
```
This runs 30 checks, S1–S30, including everything above plus SQL-shaped input, odd ids, cookie flags, CORS and malformed
bodies. It ends with **`30 passed, 0 failed`**. What each check does: [SECURITY_TESTS.md](SECURITY_TESTS.md).
It also signs up `ruth.grant@brightline.example` to test that a messily typed email still matches the list.

To see it in a browser instead: [NETWORK_TAB_CHECK.md](NETWORK_TAB_CHECK.md).
