import pandas as pd
v = pd.read_pickle("/private/tmp/claude-501/-Users-devmewada-Desktop-project-001/74f735df-028d-4236-aeb5-d4108997e5d2/scratchpad/v.pkl")
v["dup"] = v.id >= 1954
d = v[~v.dup].copy()
d["dow"] = d.si.dt.day_name(); d["hr"] = d.si.dt.hour
order = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
alld = pd.date_range("2026-07-01", "2026-09-30")
def days(excl_outage):
    s = pd.Series(alld[alld.dayofweek < 5])
    if excl_outage: s = s[~s.between("2026-08-10", "2026-08-14")]
    return s.dt.day_name().value_counts()
for label, df in [("raw w/ dups", v.assign(dow=v.si.dt.day_name(), hr=v.si.dt.hour)), ("dedup", d)]:
    c = df.dow.value_counts().reindex(order)
    print(label, "sum", c.to_dict())
    print("  per calendar weekday", (c / days(False)).reindex(order).round(2).to_dict())
    print("  per active day     ", (c / df.groupby("dow").visit_date.nunique()).reindex(order).round(2).to_dict())
    e = df[~df.visit_date.between("2026-08-10", "2026-08-14")]
    ce = e.dow.value_counts().reindex(order)
    print("  excl Aug10-14 per day", (ce / days(True)).reindex(order).round(2).to_dict())
    print("  hours", df.hr.value_counts().sort_index().to_dict())
# hour 9 spike: minute distribution
print("min dist hr9", d[d.hr == 9].si.dt.minute.value_counts().sort_index().to_dict())
print("hr16 rows", d[d.hr == 16][["visit_id","signed_in_at"]].to_string())
print("open rate by type", d.groupby("visit_type").signed_out_at.apply(lambda s: (s == "").mean()).round(2).to_dict())
print("open rate by hour", d.groupby("hr").signed_out_at.apply(lambda s: (s == "").mean()).round(2).to_dict())
print("dur by type", d.groupby("visit_type").dur.describe().round(0).to_string())
print("signout hours", d.so.dt.hour.value_counts().sort_index().to_dict())
print("signout at :00 exact", (d.so.dt.minute == 0).sum(), "signout == 17:00/18:00", d.so.dt.strftime("%H:%M").value_counts().head(5).to_dict())
# Busiest dow x hour, and dow by type
print(pd.crosstab(d.dow, d.hr).reindex(order))
print(pd.crosstab(d.visit_type, d.hr))
