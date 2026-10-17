import csv, collections, datetime as dt
P = '/Users/devmewada/Desktop/project-001/data/visits.csv'
rows = list(csv.DictReader(open(P, encoding='utf-8', newline='')))
C = collections.Counter
F = '%Y-%m-%d %H:%M:%S'
for r in rows:
    r['_in'] = dt.datetime.strptime(r['signed_in_at'], F)
    r['_n'] = int(r['visit_id'][1:])
by = {r['visit_id']: r for r in rows}
for a, b in [('V000517', 'V001968')]:
    print({k: (by[a][k], by[b][k]) for k in by[a] if not k.startswith('_') and by[a][k] != by[b][k]})
# id vs time monotonic?
srt = sorted(rows, key=lambda r: r['_n'])
inv = [(a['visit_id'], b['visit_id']) for a, b in zip(srt, srt[1:]) if b['_in'] < a['_in']]
print('id-order time inversions', len(inv), inv[:10])
# host team inconsistency counts
ht = collections.defaultdict(C)
for r in rows: ht[r['host_email']][r['host_team']] += 1
print({k: dict(v) for k, v in ht.items() if len(v) > 1})

# dedupe: drop later row of same email+date within 2 minutes
keep = []; seen = collections.defaultdict(list)
for r in sorted(rows, key=lambda r: r['_in']):
    k = (r['visitor_email'], r['visit_date'])
    if any((r['_in'] - x).total_seconds() < 120 for x in seen[k]):
        continue
    seen[k].append(r['_in']); keep.append(r)
print('kept', len(keep), 'dropped', len(rows) - len(keep))
OUT = {dt.date(2026, 8, d) for d in (10, 11, 12, 13)}
good = [r for r in keep if r['_in'].date() not in OUT]
# operating days (weekdays Jul 1 - Sep 30 minus outage)
days = []; d = dt.date(2026, 7, 1)
while d <= dt.date(2026, 9, 30):
    if d.weekday() < 5 and d not in OUT: days.append(d)
    d += dt.timedelta(days=1)
nd = C(x.strftime('%a') for x in days)
for label, data in [('raw', rows), ('dedup', keep), ('dedup-no-outage', good)]:
    wc = C(r['_in'].strftime('%a') for r in data)
    print(label, {k: wc[k] for k in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']})
print('operating days', dict(nd))
wc = C(r['_in'].strftime('%a') for r in good)
print('mean/day', {k: round(wc[k] / nd[k], 2) for k in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']})
hc = C(r['_in'].hour for r in good)
print('hour', sorted(hc.items()), 'per day', {h: round(c / len(days), 2) for h, c in sorted(hc.items())})
print('raw hour', sorted(C(r['_in'].hour for r in rows).items()))
# weekday x hour
wh = C((r['_in'].strftime('%a'), r['_in'].hour) for r in good)
print('top cells', [(k, v, round(v / nd[k[0]], 2)) for k, v in wh.most_common(5)])
# 9am without :00/:59 scheduled stamps
print('h9 excl exact 09:00/09:59', sum(1 for r in good if r['_in'].hour == 9 and r['_in'].minute not in (0, 59)))
# 30-min buckets
print('half-hour', sorted(C((r['_in'].hour, r['_in'].minute // 30 * 30) for r in good).items()))
