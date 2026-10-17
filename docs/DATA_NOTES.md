# Data notes: what's wrong with the two files

Audit scripts: `scripts/data_audit/audit.py` (broad profile) and `scripts/data_audit/deep_dive.py` (follow-ups).
Run from the project root: `python3 -I scripts/data_audit/audit.py data`.

Independent verification: two separate auditors (scripts in `scripts/data_audit/verify_a/` and `verify_b/`),
reconciled in the last section below.

---

## allowed_users.csv: 8 rows (3 admin, 5 viewer, as the brief says)

### Problem U1: two of the three admins would be locked out by naive matching ⚠️
| Line | Raw email | Issue |
|---|---|---|
| 3 | `Marcus.Vitale@Brightline.example` | uppercase letters |
| 4 | `␠ines.reyes@brightline.example␠` | leading **and** trailing space |

Plus: the whole file has Windows line endings (CRLF). Python's `csv` module handles that; a hand-split on `\n` would leave `\r` on the role (`"admin\r" != "admin"`).

**Handling:** normalise with `strip().lower()` both when loading the list and on every signup/login input.
Store the normalised email. Roles are also `strip().lower()`ed; any unknown role means **no access** (fail closed).

Checked and fine: no duplicate emails or names, all 8 on `@brightline.example`, valid ASCII, no BOM, names match emails.

---

## visits.csv: 2,011 rows, Wed 1 Jul to Wed 30 Sep 2026

### Problem V1: 58 duplicate sign-ins (double taps on the iPad) ⚠️
- 58 rows are a second copy of a visit that was already signed in, by the **same visitor, same host, same visit type, 11 to 95 seconds later**.
- Tells: all 58 have ids **V001954 to V002011** (appended at the end of the export), 57 of 58 have **non-zero seconds** in
  the timestamp (every genuine row is on `:00`), and **none of the 58 has a sign-out**. Every other field is identical to its twin.
- Example: `V001912` Sofia Reyes 15:27:00, signed out 16:38, and `V001996` Sofia Reyes 15:28:17, no sign-out.
- One duplicate (`V001968`, Aaron Demir) has no seconds, but it's 1 minute after its twin `V000517` and matches every other tell.
- A real second visit on the same day is kept: Nora Osei, `V001526` at 10:46 and `V001529` at 11:47 are both real; `V001959` at 11:47:18 is the duplicate.
- **Impact:** inflates totals by 3%, distorts busiest-day counts, and drags the "signed out" rate down.
- **Impact:** inflates totals by 2.9%, distorts busiest-day counts, drags the "signed out" rate down, and pushes 7 rows
  into a later hour. The only 4 pm sign-in in the whole file (`V002007`, 16:00:33) is a duplicate.
- **Handling:** on load, drop a row if the same visitor email + host + date signed in within **2 minutes** of an earlier
  row and the later row has no sign-out. That removes exactly the 58 → **1,953 real visits**. Log the dropped ids.
  (All three audits independently landed on the same 58 rows; the nearest genuine same-day revisit is 60+ minutes apart,
  so the threshold has lots of margin.)

### Problem V2: no data at all for Mon 10 to Thu 13 August ⚠️ (the "period the data can't be relied on")
- Four consecutive weekdays with **zero** sign-ins. Every other weekday in the quarter has 12–63. Friday 14 Aug resumes at a normal 20.
- Holidays don't explain it (no gap on 3 Jul or 7 Sep). Most likely the iPad was down or the export missed those days.
- **Impact:** any count over a range that includes that week is too low; "visits per Monday–Thursday" is pulled down if we
  divide by calendar days.
- **Handling:** treat 10–13 Aug as **no data, not zero visits**. Exclude those days from per-day averages, and show a
  plain notice whenever the selected range overlaps them: *"The lobby iPad recorded no sign-ins from Monday 10 to
  Thursday 13 August, so totals for that week are incomplete."* Ask Dana what happened.

### Finding V3: nearly half of visitors never sign out (not a bad period, a habit)
- 870 of 1,953 real visits (45%) have no sign-out. The rate is flat across all months, weekdays, hours, teams and visit types (39–50%).
- **Impact:** visit length can only be measured for the 55% who signed out, and those may not be typical.
- **Handling:** show visit length only when known, label the average as *"based on the 1,083 visits where the guest signed out"*,
  and show "Didn't sign out" on a single visit rather than a blank.

### Finding V4: busiest day depends on doing the maths properly
The range starts and ends on a Wednesday, so it has 14 Wednesdays and 13 of every other weekday. After losing
10–13 Aug (V2), it has 13 days of data for Wed and Fri and 12 for Mon, Tue and Thu.

| | Raw sum (with duplicates) | Sum after de-dup | **Average per day with data** |
|---|---|---|---|
| Mon | 315 | 305 | 25.4 |
| Tue | 487 | 475 | **39.6** |
| Wed | **521** | **509** | 39.2 |
| Thu | 441 | 423 | 35.2 |
| Fri | 247 | 241 | 18.5 |

A naive sum says **Wednesday**. Per day of data, **Tuesday and Wednesday are tied (~39–40 visits)**. Thursday follows, and
Monday and Friday are clearly quiet. **Handling:** the stats endpoint returns *average visits per day* (dividing by days
that have data) alongside the raw counts, and the headline says "Tuesdays and Wednesdays" when the difference is under ~5%.

### Finding V5: the hour pattern
- Sign-ins by hour (de-duplicated): **9 am 726**, 10 am 252, 11 am 270, **12 pm 0**, 1 pm 241, 2 pm 230, 3 pm 234. Nothing before 9 or after 4.
- 9 am really is the peak: it's high across the whole hour, not just one artefact minute. There are bumps at exactly
  `:00` in every hour (scheduled interviews), and 33 at `09:59`, which is odd but too small to change the answer.
- No sign-ins 12:00–12:59 on any day. Looks like the lobby or desk closes at lunch. Worth confirming with Dana.
- **Every single interview (495 after removing duplicates) signs in during the 9 o'clock hour.** That's most of the 9 am peak. Leave
  interviews out and the busiest hour for guests, contractors and vendors is **11 am** (270 vs 231 at 9).
- **Handling:** busiest hour is **9–10 am** by a wide margin. The by-hour chart shows all hours 9–15 including a visible
  zero at 12. Because the stats respond to the visit-type filter, Dana will see the 11 am answer as soon as she filters
  out interviews. Worth one sentence in the note: "the 9 am rush is your interview schedule".

### Finding V5b: long visits
Visit length ranges from 10 to 517 minutes (median 79). Nine visits run over 6 hours, mostly contractors, and 36 people
sign out after 7 pm. These are plausible, so we keep them, but we show the **median** visit length rather than the
mean so a few all-day contractors don't skew it.

### Finding V6: three hosts appear under two teams
`rafael.mbeki` (Sales 37 / Engineering 26), `henrik.moreau` (Engineering 34 / Recruiting 31), `idris.brandt`
(Engineering 26 / Marketing 34), interleaved across the whole quarter (not a team move on one date).
**Handling:** count each visit under the team on that row (that's what the iPad recorded) and mention it to Dana.

### Finding V7: names collide everywhere, which matters for the leak test
- **5 of the 8 app users share a name with a visitor**: Marcus Vitale, Kenji Tanaka, Priya Raghunathan, Jonas Lindqvist, Ruth Grant.
- **60 host names are also visitor names** (e.g. Mei Tanaka, Rafael Mbeki).
- 76 visitor emails are shared by two different names (e.g. `aoyelaran@bellwetherlo.example` = Amara and Aaron Oyelaran), and
  most names appear with several emails. Visitor email is **not** a person id.
- **Impact:**
  - Hiding host names from viewers (already decided) is required, not optional. Otherwise the reviewers' grep for a visitor name would hit a host name.
  - The viewer's own name must not be in `/api/visits` responses (only `/api/me`).
  - Our automated leak test must grep only data endpoints, or it gets false positives from `/api/me`.
- **Test viewer account:** use **Sam Ferreira** (name not in the visit data). **Test admin:** Dana Whitfield.

### Finding V8: tiny groups (privacy, for the note)
520 of 1,016 (day × visit type × host team) combinations contain exactly one visit. A viewer can't see who, but could
infer "the one interview Legal hosted on 3 Sep". Out of scope to fix; mention in the note as what we'd do with real data
(suppress counts below a threshold).

### Checked and fine
UTF-8, no BOM, CRLF everywhere (fine with `csv`), 12 columns on every row, ids `V000001`–`V002011` with no gaps or
duplicates, `visit_date` always equals the sign-in date, one timestamp format, no sign-out before sign-in, no overnight
visits, longest visit 8.6 h, visit types are 4 clean lowercase values (`guest`, `interview`, `contractor`, `vendor`),
8 clean host teams, `pre_registered` is always `true`/`false`, 16 companies each with one email domain, 67 hosts all on
`@brightline.example`, no visitor is an employee, no test/junk rows. Timestamps have no time zone, so we treat them as office local time.

---

## Questions for Dana
1. What happened 10–13 August? Was the iPad offline?
2. Is the lobby closed 12–1? (No sign-ins at all in that hour.)
3. Rafael Mbeki, Henrik Moreau and Idris Brandt each appear under two teams. Which is right?
4. Time zone of the iPad clock (we're assuming office local time).

---

## Implementation gotchas the audit surfaced
- **Inclusive end date:** filter on `date(signed_in_at) BETWEEN from AND to`, not `signed_in_at < to`. Otherwise
  "to 30 Sep" silently drops all 46 visits on 30 Sep.
- **Sort by `signed_in_at`**, not `visit_id`. Ids don't follow time order (the appended duplicates, among other reasons).
- **Visitor identity:** if we ever count unique or repeat visitors, use email + name, not email alone (Finding V7).

## Independent verification
Two auditors checked the raw files blind (no access to this note or the scripts above). Their scripts are in
`scripts/data_audit/verify_a/` and `verify_b/`.

| Finding | Me | Auditor A | Auditor B |
|---|---|---|---|
| U1 email case + spaces (2 of 3 admins) | ✅ | ✅ | ✅ |
| CRLF line endings | ✅ | ✅ | ✅ |
| V1 58 duplicate sign-ins, same 58 ids | ✅ | ✅ | ✅ |
| V2 no data 10–13 Aug | ✅ | ✅ | ✅ (ids continue across the gap, so it's a capture outage, not deleted rows) |
| V3 ~45% never sign out, evenly spread | ✅ | ✅ | ✅ |
| V4 Wednesday wins raw totals; Tue ≈ Wed per day | ✅ | ✅ | ✅ |
| V5 9 am peak, nothing 12–1 | ✅ | ✅ | ✅ |
| All interviews at 9 am; 11 am is busiest without them | ➕ added after B | partial | ✅ |
| V5b long visits, use median | ➕ added after A | ✅ | ✅ |
| V6 three hosts in two teams | ✅ | ✅ | ✅ |
| V7 name collisions (users and hosts vs visitors) | ✅ | ✅ | ✅ |
| Inclusive end date bug | ➕ added after B | – | ✅ |

**Corrections made after verification:** the duplicate gap is 11–95 seconds (I'd written "up to 4 minutes"); the
range has 14 Wednesdays, not 13; dedupe threshold tightened from 5 to 2 minutes.
**Disagreement:** Auditor B suggests forcing one team per host. We keep the team recorded on each visit, because
we can't know which is right, and ask Dana instead. **No auditor found anything outside this list.**
