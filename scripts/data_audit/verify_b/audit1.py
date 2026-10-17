import pandas as pd, re, sys
from collections import Counter
D = "/Users/devmewada/Desktop/project-001/data/"
raw = open(D + "visits.csv", "rb").read()
print("bytes", len(raw), "BOM", raw[:3] == b"\xef\xbb\xbf", "CRLF", raw.count(b"\r\n"), "nonascii", sum(b > 127 for b in raw))
v = pd.read_csv(D + "visits.csv", dtype=str, keep_default_na=False)
print(v.shape)
for c in v.columns:
    s = v[c]
    print(f"{c:16} uniq={s.nunique():5} blank={(s=='').sum():4} ws={(s!=s.str.strip()).sum()}")
print(v.visit_type.value_counts(), v.pre_registered.value_counts(), v.host_team.value_counts(), sep="\n")
# ids
ids = v.visit_id.str[1:].astype(int)
print("dup ids", v.visit_id.duplicated().sum(), "min/max", ids.min(), ids.max(), "missing", len(set(range(ids.min(), ids.max()+1)) - set(ids)))
# file order
si = pd.to_datetime(v.signed_in_at, errors="coerce"); so = pd.to_datetime(v.signed_out_at, errors="coerce")
print("unparseable in", (si.isna()).sum(), "out", ((so.isna()) & (v.signed_out_at != "")).sum())
print("sorted by signin", si.is_monotonic_increasing)
print("date mismatch visit_date vs signin", (v.visit_date != si.dt.strftime("%Y-%m-%d")).sum())
sec = si.dt.second != 0
print("nonzero seconds in", sec.sum(), "out", ((so.dt.second != 0) & so.notna()).sum())
print(v[sec].head(10).to_string())
print("seconds rows id range", ids[sec].min(), ids[sec].max(), "types", v[sec].visit_type.value_counts().to_dict())
fmt = Counter(re.sub(r"\d", "9", x) for x in v.signed_in_at); print(fmt)
fmt = Counter(re.sub(r"\d", "9", x) for x in v.signed_out_at); print(fmt)
fmt = Counter(re.sub(r"\d", "9", x) for x in v.visit_date); print(fmt)
dur = (so - si).dt.total_seconds() / 60
print("dur describe", dur.describe())
print("neg/zero", (dur <= 0).sum(), ">12h", (dur > 720).sum(), "crosses midnight", ((so.dt.date != si.dt.date) & so.notna()).sum())
print(v[dur <= 0].head().to_string()); print(v[dur > 600].head().to_string())
print("hour dist", si.dt.hour.value_counts().sort_index().to_dict())
print("open visits", (v.signed_out_at == "").sum())
v["si"] = si; v["so"] = so; v["dur"] = dur; v["id"] = ids
v.to_pickle("/private/tmp/claude-501/-Users-devmewada-Desktop-project-001/74f735df-028d-4236-aeb5-d4108997e5d2/scratchpad/v.pkl")
