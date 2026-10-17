import pandas as pd, csv
D = "/Users/devmewada/Desktop/project-001/data/"
raw = open(D + "allowed_users.csv", "rb").read()
print(repr(raw))
print("nonascii", [b for b in raw if b > 127], "BOM", raw[:3])
rows = list(csv.DictReader(open(D + "allowed_users.csv", newline="")))
for r in rows:
    e = r["email"]
    print(repr(e), "| norm:", e.strip().lower(), "| exact==norm:", e == e.strip().lower(), "| role:", repr(r["role"]), "| name:", repr(r["name"]))
v = pd.read_pickle("/private/tmp/claude-501/-Users-devmewada-Desktop-project-001/74f735df-028d-4236-aeb5-d4108997e5d2/scratchpad/v.pkl")
for r in rows:
    n = r["name"]; first, last = n.split(" ", 1)
    vis = v[v.visitor_name == n]; hst = v[v.host_name == n]
    print(f"{n:20} role={r['role']:6} as_visitor={len(vis):3} ids={vis.visit_id.tolist()[:5]} as_host={len(hst)} host_email={hst.host_email.unique().tolist()}  email_in_hosts={r['email'].strip().lower() in set(v.host_email)}")
    sub = v[(v.visitor_name.str.contains(n, case=False)) | v.host_name.str.contains(n, case=False)]
# hosts with two teams: is split temporal?
d = v[v.id < 1954]
for h in ["henrik.moreau", "idris.brandt", "rafael.mbeki"]:
    s = d[d.host_email.str.startswith(h)].sort_values("si")
    print(h, s.groupby("host_team").visit_date.agg(["min", "max", "size"]).to_string())
    print("  switches in time order:", (s.host_team != s.host_team.shift()).sum() - 1)
    print("  host_name variants", s.host_name.unique())
# Same host name, different people? check visitor-name/host-name both same email first-name ambiguity done. Count teams per host overall
print(d.groupby("host_email").host_team.first().value_counts().to_dict())
