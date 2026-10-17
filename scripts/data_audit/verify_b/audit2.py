import pandas as pd
v = pd.read_pickle("/private/tmp/claude-501/-Users-devmewada-Desktop-project-001/74f735df-028d-4236-aeb5-d4108997e5d2/scratchpad/v.pkl")
tail = v[v.id >= 1950].sort_values("id")
print(tail[["visit_id","signed_in_at","signed_out_at","visitor_name","visitor_email","host_name","visit_type"]].to_string())
# does each appended row have a near-duplicate original?
orig = v[v.id < 1954]
res = []
for _, r in v[v.id >= 1954].iterrows():
    m = orig[(orig.visitor_email == r.visitor_email) & (orig.visit_date == r.visit_date)]
    gap = ((r.si - m.si).dt.total_seconds()).tolist()
    same = [(a.host_email == r.host_email, a.visit_type == r.visit_type, a.signed_out_at != "") for _, a in m.iterrows()]
    res.append((r.visit_id, len(m), gap, same))
for x in res: print(x)
print("appended w/o match", sum(1 for x in res if x[1] == 0))
# id order vs time order among originals
print("orig ids sorted by time?", (orig.sort_values(["si","id"]).id.diff().dropna() > 0).mean())
# generic duplicate check: same email+date within 10 min
v2 = v.sort_values(["visitor_email","si"])
g = v2.groupby("visitor_email").si.diff().dt.total_seconds()
print("same email repeat within 10 min:", ((g >= 0) & (g < 600)).sum())
print("same email same day:", v.duplicated(["visitor_email","visit_date"]).sum())
