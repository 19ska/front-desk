import pandas as pd
v = pd.read_pickle("/private/tmp/claude-501/-Users-devmewada-Desktop-project-001/74f735df-028d-4236-aeb5-d4108997e5d2/scratchpad/v.pkl")
d = v[v.id < 1954].copy()  # dedup
d["date"] = pd.to_datetime(d.visit_date)
alld = pd.date_range("2026-07-01", "2026-09-30")
per = d.groupby("date").size().reindex(alld, fill_value=0)
print("days with 0 visits:", [(x.date(), x.day_name()) for x in per[per == 0].index])
wk = per[per.index.dayofweek < 5]
print("weekday counts in range:", pd.Series(alld.day_name()).value_counts().to_dict())
print("weekend visits:", (d.date.dt.dayofweek >= 5).sum())
print(d[d.date.dt.dayofweek >= 5][["visit_id","visit_date","signed_in_at","visit_type"]].to_string())
# daily series with signout rate
day = d.groupby("date").agg(n=("id","size"), open=("signed_out_at", lambda s: (s=="").mean()), h9=("si", lambda s: (s.dt.hour==9).mean()), min00=("si", lambda s: (s.dt.minute==0).mean()))
pd.set_option("display.max_rows", 200)
print(day.to_string())
