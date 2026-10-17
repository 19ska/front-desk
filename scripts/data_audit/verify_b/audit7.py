import pandas as pd
v = pd.read_pickle("/private/tmp/claude-501/-Users-devmewada-Desktop-project-001/74f735df-028d-4236-aeb5-d4108997e5d2/scratchpad/v.pkl")
d = v[v.id < 1954]
print("ids monotonic by visit_date:", d.sort_values("id").visit_date.is_monotonic_increasing)
s = d.sort_values("id"); print("id vs date breaks", (s.visit_date < s.visit_date.shift()).sum())
print("Aug 7 / Aug 14 ids", d[d.visit_date.isin(["2026-08-07","2026-08-14"])].id.agg(["min","max"]).to_dict())
print("non-contractor signout >=18h", d[(d.so.dt.hour >= 18) & (d.visit_type != "contractor")].shape[0])
print("dup rows on 9/30 15:xx or later that cross hour bucket:", v[(v.id>=1954) & (v.si.dt.hour != (v.si - pd.Timedelta(seconds=95)).dt.hour)][["visit_id","signed_in_at"]].to_string())
print("Sept 30 rows", (v.visit_date=="2026-09-30").sum(), "if filter to '2026-09-30 00:00' excluded")
