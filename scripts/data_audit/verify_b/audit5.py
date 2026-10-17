import pandas as pd
v = pd.read_pickle("/private/tmp/claude-501/-Users-devmewada-Desktop-project-001/74f735df-028d-4236-aeb5-d4108997e5d2/scratchpad/v.pkl")
d = v[v.id < 1954].copy()
d["hm"] = d.si.dt.strftime("%H:%M")
print("top hh:mm", d.hm.value_counts().head(12).to_dict())
print("9:00 by type", d[d.hm == "09:00"].visit_type.value_counts().to_dict())
print("minute :00 by hour", d[d.si.dt.minute == 0].si.dt.hour.value_counts().sort_index().to_dict())
print("minute :59 by hour", d[d.si.dt.minute == 59].si.dt.hour.value_counts().sort_index().to_dict())
print("interview minute range", d[d.visit_type=="interview"].si.dt.strftime("%H:%M").agg(["min","max"]).to_dict())
print("non-interview hours", d[d.visit_type!="interview"].si.dt.hour.value_counts().sort_index().to_dict())
# Host consistency
h = d.groupby("host_email").agg(names=("host_name","nunique"), teams=("host_team","nunique"))
print("hosts w/ >1 name", (h.names > 1).sum(), " >1 team", (h.teams > 1).sum())
print(d[d.host_email.isin(h[h.teams > 1].index)].groupby(["host_email","host_team"]).size().head(40).to_string())
hn = d.groupby("host_name").host_email.nunique(); print("host names w/ >1 email", (hn > 1).sum())
# email local part vs name
def exp(r):
    f, l = r.host_name.lower().split(" ", 1); return f"{f}.{l.replace(' ','')}@brightline.example"
print("host email != name pattern", (d.apply(exp, axis=1) != d.host_email).sum())
def vexp(r):
    f, l = r.visitor_name.lower().split(" ", 1); return (f[0] + l.replace(" ", ""))
loc = d.visitor_email.str.split("@").str[0]
print("visitor local != initial+last", (d.apply(vexp, axis=1) != loc).sum())
print(d[d.apply(vexp, axis=1) != loc][["visit_id","visitor_name","visitor_email"]].head(10).to_string())
# same email -> multiple names / companies
e = d.groupby("visitor_email").agg(n=("visitor_name","nunique"), names=("visitor_name", lambda s: sorted(set(s))), c=("visitor_company","nunique"))
print("emails with >1 name", (e.n > 1).sum()); print(e[e.n > 1].head(15).to_string())
print("emails with >1 company", (e.c > 1).sum())
dom = d.visitor_email.str.split("@").str[1]
print("domain->company many", d.groupby(dom).visitor_company.nunique().gt(1).sum(), "company->domain many", d.groupby("visitor_company").apply(lambda g: g.visitor_email.str.split('@').str[1].nunique()).gt(1).sum())
print(d.groupby("visitor_company").apply(lambda g: sorted(set(g.visitor_email.str.split('@').str[1]))).to_string())
# visitors with company = Brightline (internal?) and host-as-visitor
print("visitor domain brightline.example", (dom == "brightline.example").sum())
print("visitor names that are also host names", sorted(set(d.visitor_name) & set(d.host_name))[:30], len(set(d.visitor_name) & set(d.host_name)))
print("visitor emails case/ws variants", (d.visitor_email != d.visitor_email.str.lower().str.strip()).sum(), (d.host_email != d.host_email.str.lower()).sum())
# pre_registered vs type
print(pd.crosstab(d.visit_type, d.pre_registered))
