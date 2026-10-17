import csv, collections, datetime as dt
P = '/Users/devmewada/Desktop/project-001/data/visits.csv'
rows = list(csv.DictReader(open(P, encoding='utf-8', newline='')))
C = collections.Counter
F = '%Y-%m-%d %H:%M:%S'
for r in rows:
    r['_in'] = dt.datetime.strptime(r['signed_in_at'], F)
    r['_out'] = dt.datetime.strptime(r['signed_out_at'], F) if r['signed_out_at'] else None

# 9am spike
nine = [r for r in rows if r['_in'].hour == 9]
print('9h minute dist', sorted(C(r['_in'].minute for r in nine).items())[:15])
exact9 = [r for r in rows if r['_in'].strftime('%H:%M:%S') == '09:00:00']
print('exact 09:00:00', len(exact9), 'days', len(set(r['visit_date'] for r in exact9)))
print('exact9 signout blank', sum(1 for r in exact9 if not r['_out']), 'pre_reg', C(r['pre_registered'] for r in exact9), 'type', C(r['visit_type'] for r in exact9))
print('exact9 per date', sorted(C(r['visit_date'] for r in exact9).items())[:20])
print('top timestamps', C(r['_in'].strftime('%H:%M:%S') for r in rows).most_common(8))
# non-zero seconds
ns = [r for r in rows if r['_in'].second]
print('nonzero sec', len(ns), [(r['visit_id'], r['signed_in_at'], r['signed_out_at']) for r in ns[:8]])
print('nonzero sec dates', sorted(C(r['visit_date'] for r in ns).items()))
print('nonzero sec signout seconds', sum(1 for r in rows if r['_out'] and r['_out'].second))
print('16h', [(r['visit_id'], r['signed_in_at']) for r in rows if r['_in'].hour >= 16])
print('signout hours', sorted(C(r['_out'].hour for r in rows if r['_out']).items()))
# order
print('ids sorted by time?', sum(1 for a, b in zip(rows, rows[1:]) if a['_in'] > b['_in']), 'out-of-order pairs')
# Aug 14 and surroundings
for d in ['2026-08-07', '2026-08-14', '2026-08-17']:
    sub = [r for r in rows if r['visit_date'] == d]
    print(d, len(sub), 'blank out', sum(1 for r in sub if not r['_out']), 'exact9', sum(1 for r in sub if r['_in'].strftime('%H:%M') == '09:00'))
# missing signout by month/date
print('blank signout by month', C(r['visit_date'][:7] for r in rows if not r['_out']), C(r['visit_date'][:7] for r in rows))

# visitor identity
by_email = collections.defaultdict(set)
for r in rows: by_email[r['visitor_email']].add(r['visitor_name'])
multi = {e: n for e, n in by_email.items() if len(n) > 1}
print('emails with >1 name', len(multi), list(multi.items())[:8])
lc = collections.defaultdict(set)
for r in rows: lc[r['visitor_email'].lower().strip()].add(r['visitor_email'])
print('email case variants', [v for v in lc.values() if len(v) > 1][:8])
print('emails with uppercase', sum(1 for r in rows if r['visitor_email'] != r['visitor_email'].lower()))
by_name = collections.defaultdict(set)
for r in rows: by_name[r['visitor_name']].add(r['visitor_email'])
print('names with >1 email', sum(1 for v in by_name.values() if len(v) > 1), 'distinct names', len(by_name), 'distinct emails', len(by_email))
nl = collections.defaultdict(set)
for r in rows: nl[' '.join(r['visitor_name'].lower().split())].add(r['visitor_name'])
print('name case/space variants', [v for v in nl.values() if len(v) > 1][:8])
bad_email = [r['visit_id'] for r in rows if r['visitor_email'].count('@') != 1 or ' ' in r['visitor_email']]
print('malformed visitor email', len(bad_email), bad_email[:5])

# hosts
hm = collections.defaultdict(set)
for r in rows: hm[r['host_email']].add((r['host_name'], r['host_team']))
print('hosts', len(hm), [(k, v) for k, v in hm.items() if len(v) > 1][:8])
hn = collections.defaultdict(set)
for r in rows: hn[r['host_name']].add(r['host_email'])
print('host names >1 email', [(k, v) for k, v in hn.items() if len(v) > 1])

# near dups: same visitor email & date
g = collections.defaultdict(list)
for r in rows: g[(r['visitor_email'], r['visit_date'])].append(r)
nd = [v for v in g.values() if len(v) > 1]
print('same email same day groups', len(nd), 'extra rows', sum(len(v) - 1 for v in nd))
for v in nd[:8]:
    print('  ', [(r['visit_id'], r['signed_in_at'][11:], r['signed_out_at'][11:], r['host_name'], r['visit_type']) for r in v])
gaps = sorted(min(abs((a['_in'] - b['_in']).total_seconds()) / 60 for b in v if b is not a) for v in nd for a in v)
print('gap minutes within groups', C(int(x) for x in gaps).most_common(15))
# same name same day
g2 = collections.defaultdict(list)
for r in rows: g2[(r['visitor_name'].lower(), r['visit_date'])].append(r)
print('same name same day groups', sum(1 for v in g2.values() if len(v) > 1))

# name leak overlap
P2 = '/Users/devmewada/Desktop/project-001/data/allowed_users.csv'
au = list(csv.DictReader(open(P2, encoding='utf-8', newline='')))
vnames = set(r['visitor_name'] for r in rows)
hnames = set(r['host_name'] for r in rows)
print('visitor names that are also host names', sorted(vnames & hnames)[:20], len(vnames & hnames))
print('allowed names that are visitors', [a['name'] for a in au if a['name'] in vnames], 'hosts', [a['name'] for a in au if a['name'] in hnames])
ae = set(a['email'].strip().lower() for a in au)
print('allowed emails appearing as host/visitor', [e for e in ae if e in set(r['host_email'].lower() for r in rows) | set(r['visitor_email'].lower() for r in rows)])
# visitor name substrings in companies/host fields
comp = set(r['visitor_company'] for r in rows)
vfirst = set(n.split()[0] for n in vnames); vlast = set(n.split()[-1] for n in vnames)
print('visitor names inside company/host/team strings', [n for n in vnames if any(n in s for s in comp | hnames - {n})][:10])
print('visitor last names in companies', sorted(l for l in vlast if any(l in c for c in comp))[:20])
print('visitor email domains brightline', sum(1 for r in rows if 'brightline.example' == r['visitor_email'].split('@')[1]))
print('companies', len(comp), sorted(comp)[:60])
