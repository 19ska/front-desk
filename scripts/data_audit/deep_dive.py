"""Follow-up checks on the suspicious patterns audit.py found.

    python3 -I scripts/data_audit/deep_dive.py [data_dir]
"""

import csv
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")

with (DATA / "visits.csv").open(newline="", encoding="utf-8") as f:
    recs = list(csv.DictReader(f))
for r in recs:
    r["_in"] = datetime.strptime(r["signed_in_at"], "%Y-%m-%d %H:%M:%S")
    r["_out"] = datetime.strptime(r["signed_out_at"], "%Y-%m-%d %H:%M:%S") if r["signed_out_at"] else None
    r["_n"] = int(r["visit_id"][1:])


def h(t):
    print(f"\n--- {t}")


h("rows with non-zero seconds: id range and properties")
sec = [r for r in recs if r["_in"].second]
print(f"count={len(sec)} ids {min(r['_n'] for r in sec)}..{max(r['_n'] for r in sec)}")
print(f"signed out: {sum(1 for r in sec if r['_out'])}")
tail = [r for r in recs if r["_n"] >= min(r["_n"] for r in sec)]
print(f"all rows with id >= that: {len(tail)}; with seconds: {sum(1 for r in tail if r['_in'].second)}")
for r in tail:
    if not r["_in"].second:
        print(f"  tail row without seconds: {r['visit_id']} {r['signed_in_at']} {r['visitor_name']}")

h("near-duplicate pairs: does every seconds-row have a twin?")
by_key = defaultdict(list)
for r in recs:
    by_key[(r["visitor_email"], r["host_email"], r["visit_type"], r["_in"].date())].append(r)
orphans = []
for r in sec:
    twins = [o for o in by_key[(r["visitor_email"], r["host_email"], r["visit_type"], r["_in"].date())]
             if o is not r and not o["_in"].second and abs((o["_in"] - r["_in"]).total_seconds()) <= 600]
    if not twins:
        orphans.append(r)
    elif len(twins) > 1:
        print(f"  {r['visit_id']} has {len(twins)} twins")
print(f"seconds-rows without a twin: {len(orphans)}")
for r in orphans:
    print(f"  {r['visit_id']} {r['signed_in_at']} {r['visitor_name']} {r['visitor_email']}")
diff_cols = Counter()
for r in sec:
    for o in by_key[(r["visitor_email"], r["host_email"], r["visit_type"], r["_in"].date())]:
        if o is not r and not o["_in"].second:
            for c in ("visitor_name", "visitor_company", "host_name", "host_team", "pre_registered"):
                if o[c] != r[c]:
                    diff_cols[c] += 1
print(f"fields that differ between twins: {dict(diff_cols) or 'none'}")

h("the pair found by audit.py that has no seconds")
by_pd = defaultdict(list)
for r in recs:
    by_pd[(r["visitor_email"], r["_in"].date())].append(r)
for k, lst in by_pd.items():
    lst.sort(key=lambda r: r["_in"])
    for a, b in zip(lst, lst[1:]):
        if (b["_in"] - a["_in"]).total_seconds() <= 600 and not a["_in"].second and not b["_in"].second:
            for x in (a, b):
                print(f"  {x['visit_id']} {x['signed_in_at']} out={x['signed_out_at'] or '-'} "
                      f"{x['visitor_name']} host={x['host_name']} {x['visit_type']}")
    if len(lst) == 3:
        print("  three visits one day:")
        for x in lst:
            print(f"    {x['visit_id']} {x['signed_in_at']} out={x['signed_out_at'] or '-'} {x['visitor_name']}")

h("the 9 am spike: minute distribution inside 09:xx")
nine = [r for r in recs if r["_in"].hour == 9]
mins = Counter(r["_in"].minute for r in nine)
print(f"09:00 exactly: {mins[0]} of {len(nine)}; next most common minutes: {mins.most_common(6)}")
all_min = Counter(r["_in"].strftime("%H:%M") for r in recs)
print(f"most common exact times overall: {all_min.most_common(10)}")
on_hour = Counter(r["_in"].hour for r in recs if r["_in"].minute == 0 and r["_in"].second == 0)
print(f"sign-ins at exactly HH:00:00 by hour: {dict(sorted(on_hour.items()))}")
at9 = [r for r in recs if r["_in"].strftime("%H:%M:%S") == "09:00:00"]
print(f"09:00:00 rows: signed out {sum(1 for r in at9 if r['_out'])}/{len(at9)}; "
      f"types {Counter(r['visit_type'] for r in at9)}; prereg {Counter(r['pre_registered'] for r in at9)}")
per_day = Counter(r["_in"].date() for r in at9)
print(f"09:00:00 rows per day: min={min(per_day.values())} max={max(per_day.values())} days={len(per_day)}")
by_month = Counter(r["_in"].strftime("%Y-%m") for r in at9)
print(f"09:00:00 rows by month: {dict(sorted(by_month.items()))}")
before9 = sum(1 for r in recs if r["_in"].hour < 9)
print(f"sign-ins before 09:00: {before9}")
print("09:xx minute histogram (minute: count):")
print("  " + " ".join(f"{m}:{mins[m]}" for m in range(60)))
for hr in (10, 11, 13, 14, 15):
    m = Counter(r["_in"].minute for r in recs if r["_in"].hour == hr)
    print(f"  {hr}:00 exactly={m[0]}  mean per other minute={sum(v for k, v in m.items() if k)/59:.1f}")
print(f"16:xx rows: {[(r['visit_id'], r['signed_in_at']) for r in recs if r['_in'].hour == 16]}")
print(f"12:xx rows: {sum(1 for r in recs if r['_in'].hour == 12)}")
lunch = Counter(r["_in"].strftime("%H:%M") for r in recs if r["_in"].hour in (11, 13))
print(f"latest 11:xx: {max(k for k in lunch if k.startswith('11'))}  earliest 13:xx: {min(k for k in lunch if k.startswith('13'))}")

h("sign-outs: time of day and missing-rate by attribute")
outs = Counter(r["_out"].hour for r in recs if r["_out"])
print(f"sign-out hours: {dict(sorted(outs.items()))}")
for col in ("visit_type", "pre_registered", "host_team"):
    t = Counter(r[col] for r in recs)
    m = Counter(r[col] for r in recs if not r["_out"])
    print(f"{col}: " + ", ".join(f"{k} {100*m[k]/t[k]:.0f}%" for k in t))
for hr in sorted({r["_in"].hour for r in recs}):
    t = [r for r in recs if r["_in"].hour == hr]
    print(f"  in-hour {hr}: missing out {100*sum(1 for r in t if not r['_out'])/len(t):.0f}% of {len(t)}")
by_month = defaultdict(lambda: [0, 0])
for r in recs:
    k = r["_in"].strftime("%Y-%m")
    by_month[k][0] += 1
    by_month[k][1] += r["_out"] is None
print(f"missing sign-out by month: {dict((k, f'{v[1]}/{v[0]}') for k, v in sorted(by_month.items()))}")
dur_by_month = defaultdict(list)
for r in recs:
    if r["_out"]:
        dur_by_month[r["_in"].strftime("%Y-%m")].append((r["_out"] - r["_in"]).total_seconds() / 60)
for k, v in sorted(dur_by_month.items()):
    v.sort()
    print(f"  {k} duration median={v[len(v)//2]:.0f} max={v[-1]:.0f}")
out_min = Counter(r["_out"].strftime("%H:%M") for r in recs if r["_out"])
print(f"most common sign-out times: {out_min.most_common(5)}")

h("the August gap")
days = Counter(r["_in"].date() for r in recs)
d = datetime(2026, 8, 3).date()
while d <= datetime(2026, 8, 21).date():
    print(f"  {d} {d:%a}: {days.get(d, 0)}")
    d += timedelta(days=1)
wk = defaultdict(list)
for day, n in days.items():
    wk[day.weekday()].append(n)
print("typical visits per weekday: " + ", ".join(
    f"{['Mon','Tue','Wed','Thu','Fri'][k]} {sorted(v)[len(v)//2]}" for k, v in sorted(wk.items())))
around = [r for r in recs if datetime(2026, 8, 7).date() <= r["_in"].date() <= datetime(2026, 8, 17).date()]
print(f"ids around the gap: {[r['visit_id'] for r in around][:3]} ... "
      f"is there an id jump? {sorted(r['_n'] for r in around if r['_n'] < 1950)[:1]}")
seq = sorted((r for r in recs if r["_n"] < 1950), key=lambda r: r["_n"])
jumps = [(a["visit_id"], a["signed_in_at"], b["visit_id"], b["signed_in_at"]) for a, b in zip(seq, seq[1:])
         if (b["_in"] - a["_in"]).days >= 2]
print(f"id-ordered gaps of >=2 days in the non-duplicate rows: {jumps}")
print("visits per weekday in each week:")
weeks = defaultdict(Counter)
for r in recs:
    weeks[r["_in"].strftime("%G-W%V")][r["_in"].strftime("%a")] += 1
for k in sorted(weeks):
    print(f"  {k}: " + " ".join(f"{dname}={weeks[k][dname]:3}" for dname in ("Mon", "Tue", "Wed", "Thu", "Fri")))

h("public holidays / zero days")
print(f"days with zero visits that are weekdays: "
      f"{[str(x) for x in (datetime(2026,7,1).date()+timedelta(i) for i in range(92)) if x.weekday()<5 and x not in days]}")
print(f"US Jul 3 (observed Jul 4) count: {days.get(datetime(2026,7,3).date(),0)}, "
      f"Sep 7 (Labor Day) count: {days.get(datetime(2026,9,7).date(),0)}")

h("id order vs time")
srt = sorted(recs, key=lambda r: r["_n"])
for a, b in zip(srt, srt[1:]):
    if b["_in"] < a["_in"] - timedelta(days=1) and b["_n"] < 1950:
        print(f"  {a['visit_id']} {a['signed_in_at']} -> {b['visit_id']} {b['signed_in_at']}")

h("hosts in two teams")
hosts = defaultdict(list)
for r in recs:
    hosts[r["host_email"]].append(r)
for e, lst in hosts.items():
    teams = Counter(r["host_team"] for r in lst)
    if len(teams) > 1:
        print(f"  {e}: {dict(teams)}")
        for t in teams:
            ds = sorted(r["_in"] for r in lst if r["host_team"] == t)
            print(f"     {t}: {ds[0]:%Y-%m-%d} .. {ds[-1]:%Y-%m-%d}")
team_of = Counter((r["host_team"]) for r in recs)
print(f"hosts per team: {dict(Counter(lst[0]['host_team'] for lst in hosts.values()))}")

h("visit_type x host_team")
x = defaultdict(Counter)
for r in recs:
    x[r["visit_type"]][r["host_team"]] += 1
for t, c in x.items():
    print(f"  {t}: {dict(c)}")

h("small groups (re-identification risk for viewers)")
cells = Counter((r["_in"].date(), r["visit_type"], r["host_team"]) for r in recs)
print(f"(day, type, team) cells with exactly 1 visit: {sum(1 for v in cells.values() if v == 1)} of {len(cells)}")

h("visitor email local part vs name")
mis = [r for r in recs if r["visitor_email"].split("@")[0] !=
       (r["visitor_name"].split()[0][0] + r["visitor_name"].split()[-1]).lower()]
print(f"rows where email != first-initial+surname: {len(mis)} {[(r['visitor_name'], r['visitor_email']) for r in mis[:5]]}")
dom = Counter((r["visitor_company"], r["visitor_email"].split("@")[1]) for r in recs)
print("company -> domain: " + "; ".join(f"{c}={d}" for (c, d) in sorted(dom)))

h("visitor names that collide with app users or hosts")
allowed_names = set()
with (DATA / "allowed_users.csv").open(newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        allowed_names.add(row["name"].strip())
vn = {r["visitor_name"] for r in recs}
hn = {r["host_name"] for r in recs}
print(f"app users who appear as visitors: {allowed_names & vn or 'none'}")
print(f"app users who appear as hosts: {allowed_names & hn or 'none'}")
surnames = {n.split()[-1] for n in allowed_names}
print(f"app-user surnames also used by visitors: {sorted(surnames & {n.split()[-1] for n in vn})}")
