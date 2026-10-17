import csv, collections, datetime as dt, sys, unicodedata

P = '/Users/devmewada/Desktop/project-001/data/visits.csv'
raw = open(P, 'rb').read()
print('bytes', len(raw), 'BOM', raw[:3] == b'\xef\xbb\xbf', 'CRLF', raw.count(b'\r\n'), 'nonascii', sum(b > 127 for b in raw))
rows = list(csv.DictReader(open(P, encoding='utf-8', newline='')))
print('rows', len(rows))
cols = list(rows[0].keys())
C = collections.Counter

# blanks / whitespace / nonascii per column
for c in cols:
    blank = [r['visit_id'] for r in rows if r[c] == '']
    ws = [r['visit_id'] for r in rows if r[c] != r[c].strip() or '  ' in r[c]]
    na = [r['visit_id'] for r in rows if any(ord(ch) > 127 for ch in r[c])]
    print(f'{c}: blank={len(blank)} {blank[:5]} ws={len(ws)} {ws[:5]} nonascii={len(na)} {na[:5]}')

for c in ['visit_type', 'host_team', 'pre_registered']:
    print(c, C(r[c] for r in rows))

# ids
ids = C(r['visit_id'] for r in rows)
print('dup ids', [(k, v) for k, v in ids.items() if v > 1][:10], sum(v - 1 for v in ids.values() if v > 1))
nums = sorted(int(r['visit_id'][1:]) for r in rows)
print('id range', nums[0], nums[-1], 'missing', len(set(range(nums[0], nums[-1] + 1)) - set(nums)))

# exact dups (excluding id)
key = lambda r: tuple(r[c] for c in cols[1:])
kc = C(key(r) for r in rows)
ex = [r['visit_id'] for r in rows if kc[key(r)] > 1]
print('exact dup rows excl id', len(ex), ex[:10])
fk = C(tuple(r.values()) for r in rows)
print('fully identical rows', sum(v - 1 for v in fk.values() if v > 1))

def ts(s):
    for f in ('%Y-%m-%d %H:%M:%S',):
        try:
            return dt.datetime.strptime(s, f)
        except ValueError:
            pass
    return None

badfmt = [(r['visit_id'], r['signed_in_at']) for r in rows if ts(r['signed_in_at']) is None]
print('bad signin fmt', len(badfmt), badfmt[:10])
badout = [(r['visit_id'], r['signed_out_at']) for r in rows if r['signed_out_at'] and ts(r['signed_out_at']) is None]
print('bad signout fmt', len(badout), badout[:10])
mism = [(r['visit_id'], r['visit_date'], r['signed_in_at']) for r in rows if not r['signed_in_at'].startswith(r['visit_date'])]
print('date mismatch', len(mism), mism[:10])

for r in rows:
    r['_in'] = ts(r['signed_in_at']); r['_out'] = ts(r['signed_out_at']) if r['signed_out_at'] else None
    r['_dur'] = (r['_out'] - r['_in']).total_seconds() / 60 if r['_in'] and r['_out'] else None
durs = [r for r in rows if r['_dur'] is not None]
print('missing signout', sum(1 for r in rows if not r['signed_out_at']))
neg = [(r['visit_id'], r['_dur']) for r in durs if r['_dur'] < 0]
zero = [r['visit_id'] for r in durs if r['_dur'] == 0]
print('neg dur', len(neg), neg[:10], 'zero', len(zero), zero[:5])
ds = sorted(r['_dur'] for r in durs)
print('dur pctl', [ds[int(len(ds) * q)] for q in (0, .01, .05, .25, .5, .75, .95, .99)], ds[-10:])
long_ = [(r['visit_id'], r['_dur'], r['signed_in_at'], r['signed_out_at']) for r in durs if r['_dur'] > 600]
print('dur>10h', len(long_), long_[:10])
cross = [r['visit_id'] for r in durs if r['_out'].date() != r['_in'].date()]
print('crosses midnight', len(cross), cross[:10])
print('dur by type', {t: sorted(r['_dur'] for r in durs if r['visit_type'] == t)[len([1 for r in durs if r['visit_type'] == t]) // 2] for t in set(r['visit_type'] for r in rows)})
print('missing signout by type', C(r['visit_type'] for r in rows if not r['signed_out_at']))

# times
print('hour dist', sorted(C(r['_in'].hour for r in rows if r['_in']).items()))
print('minute dist secs!=0', sum(1 for r in rows if r['_in'] and r['_in'].second))
print('weekday dist', sorted(C(r['_in'].strftime('%a') for r in rows if r['_in']).items()))
days = C(r['_in'].date() for r in rows if r['_in'])
d0, d1 = min(days), max(days)
print('date range', d0, d1)
d = d0
while d <= d1:
    print(d, d.strftime('%a'), days.get(d, 0), end=' | ')
    d += dt.timedelta(days=1)
print()
