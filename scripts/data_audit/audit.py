"""Data audit for the Front Desk take-home.

Reads data/visits.csv and data/allowed_users.csv as raw text (no cleaning)
and prints every oddity it can find. Run from the project root:

    python3 -I scripts/data_audit/audit.py [data_dir]
"""

import csv
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")

EXPECTED_VISIT_COLS = [
    "visit_id", "visit_date", "signed_in_at", "signed_out_at", "visitor_name",
    "visitor_email", "visitor_company", "visit_type", "host_name", "host_email",
    "host_team", "pre_registered",
]


def heading(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def raw_bytes_report(path):
    b = path.read_bytes()
    print(f"{path.name}: {len(b)} bytes")
    print(f"  BOM: {b.startswith(b'\xef\xbb\xbf')}")
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    cr = b.count(b"\r") - crlf
    print(f"  line endings: CRLF={crlf} LF-only={lf} CR-only={cr}")
    print(f"  ends with newline: {b.endswith(b'\n')}")
    try:
        text = b.decode("utf-8")
    except UnicodeDecodeError as e:
        print(f"  NOT valid UTF-8: {e}")
        text = b.decode("utf-8", errors="replace")
    odd = Counter(ch for ch in text if ord(ch) > 127 or (ord(ch) < 32 and ch not in "\r\n"))
    if odd:
        print("  non-ASCII / control chars:")
        for ch, n in odd.most_common():
            print(f"    U+{ord(ch):04X} {unicodedata.name(ch, '?')}: {n}")
    else:
        print("  all printable ASCII")
    return text


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return header, rows


def ws_issues(value):
    issues = []
    if value != value.strip():
        issues.append("leading/trailing whitespace")
    if "  " in value:
        issues.append("double space")
    if "\t" in value:
        issues.append("tab")
    return issues


def parse_dt(s):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt), fmt
        except ValueError:
            pass
    return None, None


# --------------------------------------------------------------------------
def audit_users():
    heading("allowed_users.csv")
    path = DATA / "allowed_users.csv"
    raw_bytes_report(path)
    header, rows = read_rows(path)
    print(f"  header: {header!r}")
    print(f"  data rows: {len(rows)}")

    by_norm = defaultdict(list)
    roles = Counter()
    for i, r in enumerate(rows, start=2):
        if len(r) != len(header):
            print(f"  line {i}: {len(r)} fields (expected {len(header)}): {r!r}")
            continue
        email, name, role = r
        flags = []
        for col, v in zip(header, r):
            for issue in ws_issues(v):
                flags.append(f"{col}: {issue}")
        if email.strip() != email.strip().lower():
            flags.append("email has uppercase")
        if email.count("@") != 1:
            flags.append("email doesn't have exactly one @")
        if role.strip().lower() not in ("admin", "viewer"):
            flags.append(f"unknown role {role!r}")
        elif role != role.strip().lower():
            flags.append(f"role not normalised {role!r}")
        if not name.strip():
            flags.append("blank name")
        norm = email.strip().lower()
        by_norm[norm].append((i, name, role))
        roles[role.strip().lower()] += 1
        domain = norm.split("@")[-1]
        print(f"  line {i}: {email!r:45} {name!r:24} {role!r:10} domain={domain}"
              + (f"  <-- {'; '.join(flags)}" if flags else ""))

    print(f"\n  roles (normalised): {dict(roles)}  (brief says 3 admin, 5 viewer)")
    dups = {k: v for k, v in by_norm.items() if len(v) > 1}
    print(f"  duplicate emails after normalising: {dups or 'none'}")
    names = Counter(r[1].strip().lower() for r in rows)
    print(f"  duplicate names: {[n for n, c in names.items() if c > 1] or 'none'}")
    local_parts = Counter(k.split("@")[0] for k in by_norm)
    print(f"  duplicate local parts: {[n for n, c in local_parts.items() if c > 1] or 'none'}")
    # name vs email consistency
    for k, v in by_norm.items():
        name = v[0][1].strip().lower()
        guess = name.replace(" ", ".")
        if k.split("@")[0] != guess:
            print(f"  name/email mismatch: {k} vs name {v[0][1]!r}")
    return {k: v for k, v in by_norm.items()}


# --------------------------------------------------------------------------
def audit_visits(allowed):
    heading("visits.csv")
    path = DATA / "visits.csv"
    raw_bytes_report(path)
    header, rows = read_rows(path)
    print(f"  header matches brief: {header == EXPECTED_VISIT_COLS}")
    if header != EXPECTED_VISIT_COLS:
        print(f"  header: {header!r}")
    print(f"  data rows: {len(rows)} (brief says 2,011)")

    bad_width = [(i, len(r)) for i, r in enumerate(rows, start=2) if len(r) != len(header)]
    print(f"  rows with wrong field count: {bad_width[:10] or 'none'}")
    recs = [dict(zip(header, r)) for r in rows if len(r) == len(header)]

    # ---- whitespace / blanks per column
    heading("visits: blanks and whitespace per column")
    for col in header:
        blanks = sum(1 for r in recs if r[col] == "")
        ws = sum(1 for r in recs if r[col] and ws_issues(r[col]))
        print(f"  {col:16} blank={blanks:5} whitespace-issues={ws}")

    # ---- ids
    heading("visits: visit_id")
    ids = Counter(r["visit_id"] for r in recs)
    dup_ids = {k: c for k, c in ids.items() if c > 1}
    print(f"  unique ids: {len(ids)}  duplicated ids: {len(dup_ids)} {list(dup_ids.items())[:10]}")
    fmt_bad = [k for k in ids if not (k.startswith("V") and k[1:].isdigit() and len(k) == 7)]
    print(f"  ids not matching V+6 digits: {fmt_bad[:10] or 'none'}")
    nums = sorted(int(k[1:]) for k in ids if k[1:].isdigit())
    if nums:
        missing = sorted(set(range(nums[0], nums[-1] + 1)) - set(nums))
        print(f"  id range V{nums[0]:06}..V{nums[-1]:06}, gaps: {len(missing)} {missing[:15]}")
    ordered = [r["signed_in_at"] for r in recs]
    print(f"  file sorted by signed_in_at: {ordered == sorted(ordered)}")

    # ---- timestamps
    heading("visits: dates and times")
    fmts = Counter()
    seconds_nonzero = []
    parse_fail = []
    date_mismatch = []
    out_before_in = []
    out_equal_in = []
    long_visits = []
    overnight = []
    durations = []
    for r in recs:
        tin, f_in = parse_dt(r["signed_in_at"])
        fmts[("in", f_in)] += 1
        if tin is None:
            parse_fail.append(("in", r["visit_id"], r["signed_in_at"]))
            continue
        if tin.second:
            seconds_nonzero.append(r)
        try:
            vd = datetime.strptime(r["visit_date"], "%Y-%m-%d").date()
            if vd != tin.date():
                date_mismatch.append((r["visit_id"], r["visit_date"], r["signed_in_at"]))
        except ValueError:
            parse_fail.append(("date", r["visit_id"], r["visit_date"]))
        r["_in"] = tin
        r["_out"] = None
        if r["signed_out_at"]:
            tout, f_out = parse_dt(r["signed_out_at"])
            fmts[("out", f_out)] += 1
            if tout is None:
                parse_fail.append(("out", r["visit_id"], r["signed_out_at"]))
                continue
            r["_out"] = tout
            d = (tout - tin).total_seconds() / 60
            durations.append(d)
            if d < 0:
                out_before_in.append((r["visit_id"], r["signed_in_at"], r["signed_out_at"]))
            elif d == 0:
                out_equal_in.append(r["visit_id"])
            if d > 600:
                long_visits.append((r["visit_id"], r["signed_in_at"], r["signed_out_at"]))
            if tout.date() != tin.date():
                overnight.append(r["visit_id"])
    print(f"  formats: {dict(fmts)}")
    print(f"  parse failures: {parse_fail[:10] or 'none'}")
    print(f"  visit_date != date(signed_in_at): {len(date_mismatch)} {date_mismatch[:5]}")
    print(f"  sign-in timestamps with non-zero seconds: {len(seconds_nonzero)}")
    print(f"  signed_out before signed_in: {len(out_before_in)} {out_before_in[:5]}")
    print(f"  signed_out == signed_in: {len(out_equal_in)}")
    print(f"  visits > 10h: {len(long_visits)} {long_visits[:5]}")
    print(f"  sign-out on a different day: {len(overnight)}")
    if durations:
        ds = sorted(durations)
        print(f"  duration minutes: min={ds[0]:.0f} median={ds[len(ds)//2]:.0f} "
              f"p95={ds[int(len(ds)*.95)]:.0f} max={ds[-1]:.0f}")

    ok = [r for r in recs if "_in" in r]
    if ok:
        first, last = min(r["_in"] for r in ok), max(r["_in"] for r in ok)
        print(f"  span: {first} .. {last}")
        days = Counter(r["_in"].date() for r in ok)
        all_days = [first.date() + timedelta(days=i) for i in range((last.date() - first.date()).days + 1)]
        missing_days = [d for d in all_days if d not in days]
        print(f"  calendar days with zero visits: {len(missing_days)}")
        wk = [d for d in missing_days if d.weekday() < 5]
        print(f"  weekdays with zero visits: {wk or 'none'}")
        weekend = Counter(r["_in"].strftime("%a") for r in ok if r["_in"].weekday() >= 5)
        print(f"  weekend visits: {dict(weekend) or 'none'}")
        hours = Counter(r["_in"].hour for r in ok)
        print(f"  sign-ins by hour: {dict(sorted(hours.items()))}")
        dows = Counter(r["_in"].strftime("%a") for r in ok)
        print(f"  sign-ins by weekday: {dict(dows)}")

    # ---- sign-out missing by period
    heading("visits: missing sign-out by week (the 'unreliable period' check)")
    weeks = defaultdict(lambda: [0, 0])
    for r in ok:
        key = r["_in"].strftime("%G-W%V")
        weeks[key][0] += 1
        if not r["signed_out_at"]:
            weeks[key][1] += 1
    for k in sorted(weeks):
        tot, miss = weeks[k]
        bar = "#" * int(40 * miss / tot) if tot else ""
        print(f"  {k}: {miss:4}/{tot:4} missing ({100*miss/tot:5.1f}%) {bar}")
    daily = defaultdict(lambda: [0, 0])
    for r in ok:
        daily[r["_in"].date()][0] += 1
        if not r["signed_out_at"]:
            daily[r["_in"].date()][1] += 1
    hi = [(d, m, t) for d, (t, m) in sorted(daily.items()) if t and m / t > 0.5]
    print(f"  days with >50% missing sign-out: {len(hi)}")
    for d, m, t in hi:
        print(f"    {d} {d:%a}: {m}/{t}")

    # ---- categorical columns
    heading("visits: categorical values (raw)")
    for col in ("visit_type", "host_team", "pre_registered", "visitor_company"):
        c = Counter(r[col] for r in recs)
        print(f"  {col} ({len(c)} distinct):")
        for v, n in c.most_common():
            print(f"    {v!r}: {n}")
        norm = Counter(r[col].strip().lower() for r in recs)
        if len(norm) != len(c):
            print(f"    -> only {len(norm)} distinct after trim+lowercase")

    # ---- people
    heading("visits: people")
    emails = Counter(r["visitor_email"] for r in recs)
    print(f"  distinct visitor emails: {len(emails)}, distinct names: {len(set(r['visitor_name'] for r in recs))}")
    email_names = defaultdict(set)
    name_emails = defaultdict(set)
    for r in recs:
        email_names[r["visitor_email"].strip().lower()].add(r["visitor_name"])
        name_emails[r["visitor_name"]].add(r["visitor_email"])
    multi = {e: n for e, n in email_names.items() if len(n) > 1}
    print(f"  emails used by >1 name: {len(multi)} {list(multi.items())[:5]}")
    multi = {n: e for n, e in name_emails.items() if len(e) > 1}
    print(f"  names with >1 email: {len(multi)} {list(multi.items())[:5]}")
    bad_email = [r["visitor_email"] for r in recs if r["visitor_email"].count("@") != 1]
    print(f"  malformed visitor emails: {bad_email[:10] or 'none'}")
    upper = [r["visitor_email"] for r in recs if r["visitor_email"] != r["visitor_email"].lower()]
    print(f"  visitor emails with uppercase: {len(upper)} {upper[:5]}")
    # company vs email domain
    comp_domains = defaultdict(Counter)
    for r in recs:
        comp_domains[r["visitor_company"]][r["visitor_email"].split("@")[-1].lower()] += 1
    print("  companies with >1 email domain:")
    for c, d in comp_domains.items():
        if len(d) > 1:
            print(f"    {c!r}: {dict(d)}")
    # hosts
    host_pairs = defaultdict(set)
    for r in recs:
        host_pairs[r["host_email"].strip().lower()].add((r["host_name"], r["host_team"]))
    multi = {h: p for h, p in host_pairs.items() if len(p) > 1}
    print(f"  distinct hosts: {len(host_pairs)} (brief says ~70)")
    print(f"  hosts with >1 name/team: {len(multi)} {list(multi.items())[:5]}")
    host_domains = Counter(h.split("@")[-1] for h in host_pairs)
    print(f"  host email domains: {dict(host_domains)}")
    staff_visitors = [r for r in recs if r["visitor_email"].lower().endswith("@brightline.example")]
    print(f"  visitors with an @brightline.example email: {len(staff_visitors)}")
    self_hosted = [r["visit_id"] for r in recs if r["visitor_email"].strip().lower() == r["host_email"].strip().lower()]
    print(f"  visitor == host: {self_hosted or 'none'}")
    allowed_in_visits = [r["visit_id"] for r in recs
                         if r["visitor_email"].strip().lower() in allowed
                         or r["host_email"].strip().lower() in allowed]
    print(f"  rows involving an app user (as visitor or host): {len(allowed_in_visits)}")
    hosts_names = {n for p in host_pairs.values() for n, _ in p}
    overlap = hosts_names & set(name_emails)
    print(f"  names that appear as both host and visitor: {sorted(overlap) or 'none'}")
    junk = [r for r in recs if any(w in (r["visitor_name"] + r["visitor_email"] + r["visitor_company"]).lower()
                                   for w in ("test", "asdf", "xxx", "n/a", "unknown", "dummy", "example.com"))]
    print(f"  possible test/junk rows: {len(junk)}")
    for r in junk[:10]:
        print(f"    {r['visit_id']} {r['visitor_name']!r} {r['visitor_email']!r} {r['visitor_company']!r}")

    # ---- duplicate visits
    heading("visits: duplicate / double sign-ins")
    full = Counter(tuple(r[c] for c in header[1:]) for r in recs)
    print(f"  rows identical except visit_id: {sum(c - 1 for c in full.values() if c > 1)}")
    by_person_day = defaultdict(list)
    for r in ok:
        by_person_day[(r["visitor_email"].strip().lower(), r["_in"].date())].append(r)
    close = []
    for (_, _), lst in by_person_day.items():
        lst.sort(key=lambda r: r["_in"])
        for a, b in zip(lst, lst[1:]):
            gap = (b["_in"] - a["_in"]).total_seconds()
            if gap <= 600:
                close.append((a, b, gap))
    print(f"  same visitor signed in twice within 10 min: {len(close)}")
    gaps = Counter()
    for a, b, gap in close:
        gaps["<=60s" if gap <= 60 else "<=5m" if gap <= 300 else "<=10m"] += 1
    print(f"  gap buckets: {dict(gaps)}")
    same_host = sum(1 for a, b, _ in close if a["host_email"] == b["host_email"] and a["visit_type"] == b["visit_type"])
    print(f"  ...of which same host and type: {same_host}")
    sec = sum(1 for a, b, _ in close if b["_in"].second or a["_in"].second)
    print(f"  ...of which one row has non-zero seconds: {sec}")
    print(f"  ...where the later row has no sign-out: {sum(1 for a, b, _ in close if not b['signed_out_at'])}")
    for a, b, gap in close[:8]:
        print(f"    {a['visit_id']} {a['signed_in_at']} out={a['signed_out_at'] or '-':19} | "
              f"{b['visit_id']} {b['signed_in_at']} out={b['signed_out_at'] or '-':19} gap={gap:.0f}s "
              f"{a['visitor_name']}")
    multi_day = Counter(len(v) for v in by_person_day.values())
    print(f"  visits per (visitor, day): {dict(sorted(multi_day.items()))}")
    # seconds-precision rows overall
    print(f"  all rows with non-zero seconds in sign-in: {len(seconds_nonzero)}; "
          f"of those in a near-duplicate pair: "
          f"{len({b['visit_id'] for a, b, _ in close if b['_in'].second} | {a['visit_id'] for a, b, _ in close if a['_in'].second})}")
    for r in seconds_nonzero[:5]:
        print(f"    {r['visit_id']} {r['signed_in_at']} out={r['signed_out_at'] or '-'} {r['visitor_name']}")

    # ---- id order vs time
    heading("visits: id order vs time")
    inv = 0
    srt = sorted(ok, key=lambda r: r["visit_id"])
    for a, b in zip(srt, srt[1:]):
        if b["_in"] < a["_in"] - timedelta(days=1):
            inv += 1
    print(f"  id order inversions > 1 day: {inv}")


if __name__ == "__main__":
    allowed = audit_users()
    audit_visits(allowed)
