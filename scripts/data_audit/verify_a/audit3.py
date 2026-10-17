import csv, collections, datetime as dt
P = '/Users/devmewada/Desktop/project-001/data/visits.csv'
rows = list(csv.DictReader(open(P, encoding='utf-8', newline='')))
C = collections.Counter
F = '%Y-%m-%d %H:%M:%S'
for r in rows:
    r['_in'] = dt.datetime.strptime(r['signed_in_at'], F)
    r['_out'] = dt.datetime.strptime(r['signed_out_at'], F) if r['signed_out_at'] else None
    r['_n'] = int(r['visit_id'][1:])

ns = [r for r in rows if r['_in'].second]
print('nonzero-sec id range', min(r['_n'] for r in ns), max(r['_n'] for r in ns), 'all blank out', all(not r['_out'] for r in ns))
print('ids >= min nonzero', sum(1 for r in rows if r['_n'] >= min(x['_n'] for x in ns)))
hi = [r for r in rows if r['_n'] >= 1950]
print('ids>=1950', [(r['visit_id'], r['signed_in_at']) for r in hi if not r['_in'].second])
# match each nonzero-sec row to a twin
idx = collections.defaultdict(list)
for r in rows: idx[(r['visitor_email'], r['visit_date'])].append(r)
cols = ['visitor_name', 'visitor_company', 'visit_type', 'host_name', 'host_email', 'host_team', 'pre_registered']
twin = 0; diffs = C()
for r in ns:
    cands = [x for x in idx[(r['visitor_email'], r['visit_date'])] if x is not r and abs((x['_in'] - r['_in']).total_seconds()) < 120]
    if cands:
        twin += 1
        for c in cols:
            if cands[0][c] != r[c]: diffs[c] += 1
print('nonzero-sec rows with twin <2min', twin, '/', len(ns), 'field diffs', diffs)
# other near-dups not of this kind
others = [v for v in idx.values() if len(v) > 1 and not any(x['_in'].second for x in v)]
print('other same-email-same-day groups', len(others), [[(x['visit_id'], x['signed_in_at'][11:16]) for x in v] for v in others[:5]])

# hour distribution per month & week
dedup = [r for r in rows if not r['_in'].second]
for m in ['2026-07', '2026-08', '2026-09']:
    print(m, sorted(C(r['_in'].hour for r in dedup if r['visit_date'].startswith(m)).items()))
print('hour 9 minute dist full', sorted(C(r['_in'].minute for r in dedup if r['_in'].hour == 9).items()))
print('hour 10 minute dist', sorted(C(r['_in'].minute for r in dedup if r['_in'].hour == 10).items()))
# per ISO week share of 9am
wk = collections.defaultdict(list)
for r in dedup: wk[r['_in'].isocalendar()[1]].append(r)
for w, v in sorted(wk.items()):
    print('wk', w, len(v), 'h9', sum(1 for r in v if r['_in'].hour == 9), 'blankout', sum(1 for r in v if not r['_out']), 'h', sorted(C(r['_in'].hour for r in v).items()))
# 9am by type / pre-reg
print('h9 by type', C(r['visit_type'] for r in dedup if r['_in'].hour == 9), 'all', C(r['visit_type'] for r in dedup))
print('h9 pre-reg', C(r['pre_registered'] for r in dedup if r['_in'].hour == 9))
# durations
d = [(r['_out'] - r['_in']).total_seconds() / 60 for r in dedup if r['_out']]
print('dur n', len(d), 'max', max(d), 'over 6h', sum(1 for x in d if x > 360), [(r['visit_id'], r['signed_in_at'], r['signed_out_at'], r['visit_type']) for r in dedup if r['_out'] and (r['_out'] - r['_in']).total_seconds() > 400 * 60])
print('dur exactly 10', sum(1 for x in d if x == 10), 'under 15', sum(1 for x in d if x < 15))
print('dur hist', sorted(C(int(x // 30) * 30 for x in d).items()))
print('signout after 18:00', [(r['visit_id'], r['signed_out_at']) for r in dedup if r['_out'] and r['_out'].hour >= 19][:10], sum(1 for r in dedup if r['_out'] and r['_out'].hour >= 19))
print('signout minute 0 share', sum(1 for r in dedup if r['_out'] and r['_out'].minute == 0), C(r['_out'].strftime('%H:%M') for r in dedup if r['_out']).most_common(5))
