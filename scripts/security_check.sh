#!/usr/bin/env bash
# The Front Desk: security checks S1-S30 against a running server, with curl.
# Catalogue and expected results: docs/SECURITY_TESTS.md. Hand-run walkthrough: docs/TESTING_WITH_CURL.md.
#
#   BASE=http://127.0.0.1:8000 scripts/security_check.sh
#
# Needs: bash, curl, python3 (standard library only). Creates the two test logins if missing
# (and signs up ruth.grant for S11). Read-only otherwise. Exit code 1 if anything fails.
set -u
cd "$(dirname "$0")/.." || exit 1
BASE="${BASE:-http://127.0.0.1:8000}"
BASE="${BASE%/}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASSED=0
FAILED=0

ok()   { echo "PASS  $1"; PASSED=$((PASSED + 1)); }
bad()  { echo "FAIL  $1  ($2)"; FAILED=$((FAILED + 1)); }
check() { if [ "$2" = "yes" ]; then ok "$1"; else bad "$1" "${3:-}"; fi; }

# req METHOD PATH [TOKEN] [JSON_BODY] -> $STATUS, body in $TMP/body, headers in $TMP/headers
req() {
  local args=(-s -o "$TMP/body" -D "$TMP/headers" -w '%{http_code}' -X "$1" "$BASE$2")
  [ -n "${3:-}" ] && args+=(-H "Authorization: Bearer $3")
  [ -n "${4:-}" ] && args+=(-H 'content-type: application/json' --data-binary "$4")
  STATUS="$(curl "${args[@]}")"
}
body() { cat "$TMP/body"; }
err()  { python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("error",""))' "$TMP/body" 2>/dev/null; }
is()   { [ "$1" = "$2" ] && echo yes || echo no; }
enc()  { python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"; }

# Every visitor name, visitor email, company, host name and host email in the CSV, lower-cased.
python3 - "$TMP/identities.txt" <<'PY'
import csv, sys
rows = list(csv.DictReader(open("data/visits.csv", newline="", encoding="utf-8-sig")))
cols = ("visitor_name", "visitor_email", "visitor_company", "host_name", "host_email")
open(sys.argv[1], "w").write("\n".join(sorted({r[c].strip().lower() for r in rows for c in cols})) + "\n")
PY
# leaks FILE... -> number of distinct identities that appear in the files
leaks() {
  python3 - "$TMP/identities.txt" "$@" <<'PY'
import sys
needles = [l for l in open(sys.argv[1]).read().splitlines() if l]
blob = "\n".join(open(p, encoding="utf-8", errors="replace").read().lower() for p in sys.argv[2:])
print(sum(n in blob for n in needles))
PY
}

login() {
  req POST /api/auth/login "" "{\"email\":\"$1\",\"password\":\"$2\"}"
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["token"])' "$TMP/body" 2>/dev/null
}

if ! curl -s -o /dev/null "$BASE/api/health"; then
  echo "Can't reach the app at $BASE. Start it first: .venv/bin/uvicorn app.main:app"
  exit 1
fi
python3 scripts/create_test_accounts.py --base "$BASE" > /dev/null || exit 1
VIEWER="$(login sam.ferreira@brightline.example frontdesk-viewer)"
ADMIN="$(login dana.whitfield@brightline.example frontdesk-admin)"
[ -n "$VIEWER" ] && [ -n "$ADMIN" ] || { echo "Couldn't log in as the test accounts."; exit 1; }
echo "Checking $BASE as viewer sam.ferreira and admin dana.whitfield"
echo

# --- S1-S2: no session, bad sessions -------------------------------------------------------
s1=yes; s1_detail=""
for path in /api/me /api/visit-types /api/visits /api/visits/V001912 /api/stats /api/admin/users; do
  req GET "$path"
  if [ "$STATUS" != 401 ] || [ "$(err)" != "Sign in to continue." ] || ! grep -qi '^content-type: application/json' "$TMP/headers"; then
    s1=no; s1_detail="$path -> $STATUS $(body)"
  fi
done
req POST /api/auth/logout; [ "$STATUS" = 401 ] || { s1=no; s1_detail="logout -> $STATUS"; }
check "S1  no session: every data endpoint is a JSON 401, never a redirect" $s1 "$s1_detail"

s2=yes
for header in "Authorization: Bearer nonsense" "Authorization: Basic abc" "Authorization: Bearer" "Cookie: fd_session=garbage"; do
  code="$(curl -s -o /dev/null -w '%{http_code}' -H "$header" "$BASE/api/visits")"
  [ "$code" = 401 ] || { s2=no; s2_detail="$header -> $code"; }
done
check "S2  garbage or malformed tokens and cookies get 401" $s2 "${s2_detail:-}"

# --- S3-S6: what a viewer receives -----------------------------------------------------------
req GET "/api/visits?page_size=200" "$VIEWER"
pages="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["total_pages"])' "$TMP/body")"
total="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["total"])' "$TMP/body")"
s3=yes; seen=0
for p in $(seq 1 "${pages:-0}"); do
  req GET "/api/visits?page=$p&page_size=200" "$VIEWER"; cp "$TMP/body" "$TMP/viewer-page-$p.json"
  [ "$STATUS" = 200 ] || { s3=no; s3_detail="page $p -> $STATUS"; }
  seen=$((seen + $(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["items"]))' "$TMP/body" 2>/dev/null || echo 0)))
done
# Guard against a vacuous pass: the pages must actually have held every visit.
[ "${total:-0}" -gt 0 ] && [ "$seen" = "$total" ] || { s3=no; s3_detail="saw $seen of ${total:-?} visits"; }
n="$(leaks "$TMP"/viewer-page-*.json)"; [ "$n" = 0 ] || { s3=no; s3_detail="$n identities found"; }
check "S3  viewer: all ${pages:-0} pages ($seen visits) contain none of the CSV's names, emails or companies" $s3 "${s3_detail:-}"

python3 -c 'import csv; [print(r["visit_id"]) for r in list(csv.DictReader(open("data/visits.csv")))[::40]]' > "$TMP/ids.txt"
s4=yes; found=0
while read -r id; do
  req GET "/api/visits/$id" "$VIEWER"; cp "$TMP/body" "$TMP/viewer-visit-$id.json"
  [ "$STATUS" = 200 ] && found=$((found + 1))
  { [ "$STATUS" = 200 ] || [ "$STATUS" = 404 ]; } || { s4=no; s4_detail="$id -> $STATUS"; }
  grep -q '"visitor"\|"host"' "$TMP/body" && { s4=no; s4_detail="$id has a visitor/host key"; }
done < "$TMP/ids.txt"
n="$(leaks "$TMP"/viewer-visit-*.json)"; [ "$n" = 0 ] || { s4=no; s4_detail="$n identities found"; }
[ "$found" -ge 40 ] || { s4=no; s4_detail="only $found visits returned 200"; }  # most sampled ids are real visits
check "S4  viewer: $(wc -l < "$TMP/ids.txt" | tr -d ' ') single visits across the file have no identity and no visitor/host key" $s4 "${s4_detail:-}"

s5=yes
for q in "" "?type=interview" "?from=2026-08-01&to=2026-08-31"; do
  req GET "/api/stats$q" "$VIEWER"; cp "$TMP/body" "$TMP/viewer-stats-$(enc "$q").json"
  [ "$STATUS" = 200 ] || { s5=no; s5_detail="stats$q -> $STATUS"; }
done
n="$(leaks "$TMP"/viewer-stats-*.json)"; [ "$n" = 0 ] || { s5=no; s5_detail="$n found"; }
check "S5  viewer: stats (all, per type, August) contain no identities" $s5 "${s5_detail:-}"

keys() { python3 -c 'import json,sys; print(",".join(sorted(json.load(open(sys.argv[1]))["items"][0])))' "$TMP/body"; }
req GET "/api/visits?page_size=1" "$VIEWER"; vkeys="$(keys)"
req GET "/api/visits?page_size=1" "$ADMIN";  akeys="$(keys)"
want_v="date,duration_min,host_team,pre_registered,signed_in,signed_out,visit_id,visit_type"
want_a="date,duration_min,host,host_team,pre_registered,signed_in,signed_out,visit_id,visit_type,visitor"
check "S6  same request: viewer keys are the viewer set, admin adds visitor and host" \
  "$( [ "$vkeys" = "$want_v" ] && [ "$akeys" = "$want_a" ] && echo yes || echo no)" "viewer=$vkeys admin=$akeys"

# --- S7-S9: authorisation --------------------------------------------------------------------
s7=yes
for param in "visitor_name=Sofia" "q=Sofia" "sort=visitor_name" "visitor_email=x" "host_name=Nadia" "company=Oakfield"; do
  req GET "/api/visits?$param" "$VIEWER"
  case "$(err)" in "Unknown filter:"*) [ "$STATUS" = 400 ] || s7=no ;; *) s7=no; s7_detail="$param -> $STATUS $(err)";; esac
done
check "S7  identity-shaped parameters are refused with 400 Unknown filter" $s7 "${s7_detail:-}"

req GET /api/admin/users "$VIEWER"
check "S8  viewer gets 403 from /api/admin/users and no names" \
  "$( [ "$STATUS" = 403 ] && [ "$(err)" = "You don't have access to this." ] && ! grep -qi dana "$TMP/body" && echo yes || echo no)" "$STATUS $(body)"
req GET /api/admin/users "$ADMIN"
count="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["users"]))' "$TMP/body" 2>/dev/null)"
check "S9  admin sees the access list (8 people)" "$( [ "$STATUS" = 200 ] && [ "$count" = 8 ] && echo yes || echo no)" "$STATUS $count"

# --- S10-S15: sign-up and login --------------------------------------------------------------
req POST /api/auth/signup "" '{"email":"stranger@example.com","password":"whatever123"}'
check "S10 email not on the list is refused clearly (403)" \
  "$( [ "$STATUS" = 403 ] && [ "$(err)" = "This email isn't on Brightline's access list. If you think it should be, ask Dana." ] && echo yes || echo no)" "$STATUS $(err)"

req POST /api/auth/signup "" '{"email":" Ruth.Grant@BRIGHTLINE.example ","password":"frontdesk-test"}'; s11_status="$STATUS"
ruth="$(login ruth.grant@brightline.example frontdesk-test)"
check "S11 messy case and spaces still match the list (sign up, then log in with the clean email)" \
  "$( { [ "$s11_status" = 201 ] || [ "$s11_status" = 409 ]; } && [ -n "$ruth" ] && echo yes || echo no)" "signup $s11_status"

req POST /api/auth/signup "" '{"email":"sam.ferreira@brightline.example","password":"frontdesk-viewer"}'
check "S12 signing up twice is a 409" "$(is "$STATUS" 409)" "$STATUS"

msgs=""
for pair in "sam.ferreira@brightline.example:wrong-password" "nobody@example.com:whatever123" "priya.raghunathan@brightline.example:not-signed-up"; do
  req POST /api/auth/login "" "{\"email\":\"${pair%%:*}\",\"password\":\"${pair#*:}\"}"
  msgs="$msgs$STATUS $(err)|"
done
check "S13 wrong password, unknown email, not-signed-up all give the identical 401" \
  "$(is "$msgs" "401 Email or password is incorrect.|401 Email or password is incorrect.|401 Email or password is incorrect.|")" "$msgs"

req POST /api/auth/login "" '{"email":"sam.ferreira@brightline.example","password":"frontdesk-viewer"}'
cookie="$(grep -i '^set-cookie:' "$TMP/headers" | tr -d '\r')"
s14=yes; for flag in HttpOnly "SameSite=lax" "Max-Age=28800" "Path=/"; do echo "$cookie" | grep -qi "$flag" || { s14=no; s14_detail="missing $flag"; }; done
check "S14 session cookie is HttpOnly, SameSite=Lax, 8 hours, Path=/" $s14 "${s14_detail:-$cookie}"

spare="$(login sam.ferreira@brightline.example frontdesk-viewer)"
req POST /api/auth/logout "$spare"; logout_status="$STATUS"
req GET /api/me "$spare"
check "S15 after logout the same token is refused" "$( [ "$logout_status" = 204 ] && [ "$STATUS" = 401 ] && echo yes || echo no)" "logout $logout_status, then $STATUS"

# --- S16-S19: bad input ----------------------------------------------------------------------
s16=yes
while IFS='|' read -r query expected; do
  req GET "/api/visits?$query" "$VIEWER"
  [ "$STATUS" = 400 ] && [ "$(err)" = "$expected" ] || { s16=no; s16_detail="$query -> $STATUS $(err)"; }
done <<'CASES'
from=14/08/2026|from must be a date written as YYYY-MM-DD.
to=2026-02-30|to must be a date written as YYYY-MM-DD.
from=2026-08-31&to=2026-08-01|The end date (2026-08-01) is before the start date (2026-08-31).
type=intervew|Unknown visit type 'intervew'. Choose one of: contractor, guest, interview, vendor.
page=0|page must be a whole number from 1.
page=999|Page 999 doesn't exist. There are 40 pages.
page_size=500|page_size must be a whole number from 1 to 200.
type=guest&type=vendor|Give type only once.
CASES
req GET "/api/visits?page=$(printf '9%.0s' $(seq 1 5000))" "$VIEWER"
[ "$STATUS" = 400 ] || { s16=no; s16_detail="5000-digit page -> $STATUS"; }
check "S16 bad dates, types and paging are 400s with the exact messages (never 500)" $s16 "${s16_detail:-}"

s17=yes
for payload in "' OR 1=1--" "1;DROP TABLE visits" "guest' UNION SELECT visitor_name FROM visits--"; do
  for key in type from; do
    req GET "/api/visits?$key=$(enc "$payload")" "$VIEWER"; [ "$STATUS" = 400 ] || { s17=no; s17_detail="$key=$payload -> $STATUS"; }
  done
  req GET "/api/visits/$(enc "$payload")" "$VIEWER"; [ "$STATUS" = 404 ] || { s17=no; s17_detail="id=$payload -> $STATUS"; }
done
req GET /api/stats "$VIEWER"
total="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["total_visits"])' "$TMP/body")"
[ "$total" = 1953 ] || { s17=no; s17_detail="total is now $total"; }
check "S17 SQL-shaped input is rejected and the data is untouched" $s17 "${s17_detail:-}"

s18=yes
for path in /api/auth/signup /api/auth/login; do
  for payload in "not json" "" "[]"; do
    code="$(curl -s -o "$TMP/body" -w '%{http_code}' -X POST -H 'content-type: application/json' --data-binary "$payload" "$BASE$path")"
    [ "$code" = 400 ] && [ -n "$(err)" ] || { s18=no; s18_detail="$path '$payload' -> $code"; }
  done
done
check "S18 malformed, empty or wrong-shape bodies are 400 with a message" $s18 "${s18_detail:-}"

req POST /api/auth/signup "" '{"email":"\ud800","password":"abcdefgh"}'
check "S19 text that can't be stored (lone surrogate) is a 400, not a 500" "$(is "$STATUS" 400)" "$STATUS $(body)"

# --- S20-S30: edges ---------------------------------------------------------------------------
req GET /api/nope; g="$STATUS $(err)"; req POST /api/nope; p="$STATUS $(err)"
check "S20 unknown API paths are a JSON 404 for GET and POST" \
  "$( [ "$g" = "404 No such endpoint: GET /api/nope" ] && [ "$p" = "404 No such endpoint: POST /api/nope" ] && echo yes || echo no)" "$g / $p"

req GET /no/such/page
check "S21 unknown page path is a real 404 (HTML shell)" \
  "$( [ "$STATUS" = 404 ] && grep -q '<main id="app"' "$TMP/body" && echo yes || echo no)" "$STATUS"

req GET /visits; cp "$TMP/body" "$TMP/shell.html"
check "S22 page shell needs no session and carries no data" \
  "$( [ "$STATUS" = 200 ] && [ "$(leaks "$TMP/shell.html")" = 0 ] && echo yes || echo no)" "$STATUS"

req GET /openapi.json; cp "$TMP/body" "$TMP/openapi.json"; o="$STATUS"; req GET /docs
check "S23 /docs and /openapi.json describe the API but contain no visitor data" \
  "$( [ "$o" = 200 ] && [ "$STATUS" = 200 ] && [ "$(leaks "$TMP/openapi.json")" = 0 ] && echo yes || echo no)" "openapi $o docs $STATUS"

code="$(curl -s -o /dev/null -D "$TMP/headers" -w '%{http_code}' -H "Origin: http://evil.example" -H "Authorization: Bearer $VIEWER" "$BASE/api/visits")"
check "S24 no CORS header is sent to a foreign origin" \
  "$( [ "$code" = 200 ] && ! grep -qi '^access-control-allow-origin' "$TMP/headers" && echo yes || echo no)" "$code $(grep -i access-control "$TMP/headers")"

s25=yes
for id in "%2e%2e" "$(printf 'x%.0s' $(seq 1 5000))" "%00" "V001912%2F..%2F.."; do
  req GET "/api/visits/$id" "$VIEWER"; [ "$STATUS" = 404 ] || { s25=no; s25_detail="${id:0:20} -> $STATUS"; }
done
check "S25 odd and very long ids are 404s, never 500" $s25 "${s25_detail:-}"

req GET /api/visits/V001996 "$VIEWER"; v="$STATUS $(body)"; req GET /api/visits/V001996 "$ADMIN"; a="$STATUS $(body)"
check "S26 a removed duplicate id gives the same 404 to viewer and admin" \
  "$( [ "$v" = "$a" ] && [ "${v%% *}" = 404 ] && echo yes || echo no)" "$v vs $a"

req GET "/api/visits?page_size=200" "$ADMIN"; cp "$TMP/body" "$TMP/admin-page.json"
n="$(leaks "$TMP/admin-page.json")"
check "S27 control: the same leak check on an admin's page finds names (so S3-S5 can see a leak)" \
  "$( [ "$n" -gt 50 ] && echo yes || echo no)" "$n found"

req GET /visits/V001912
check "S28 the HTML shell is text/html with no stack traces" \
  "$(grep -qi '^content-type: text/html' "$TMP/headers" && ! grep -qi traceback "$TMP/body" && echo yes || echo no)" ""

req GET "/api/visits?page_size=200" "$VIEWER"
items="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["items"]))' "$TMP/body")"
check "S29 the biggest page is capped at 200 items" "$( [ "$items" -le 200 ] && echo yes || echo no)" "$items"

req GET /api/stats "$VIEWER"; v="$STATUS $(body)"; req GET /api/stats "$ADMIN"; a="$STATUS $(body)"
check "S30 stats are identical for viewer and admin (aggregates only)" \
  "$( [ "$v" = "$a" ] && [ "${v%% *}" = 200 ] && echo yes || echo no)" "${v:0:40} vs ${a:0:40}"

echo
echo "$PASSED passed, $FAILED failed"
[ "$FAILED" = 0 ]
