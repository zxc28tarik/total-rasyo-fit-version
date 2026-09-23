import json, os, sys
from datetime import timedelta
sys.path.insert(0, r"C:\Users\zxc28\Desktop\totalrasyofitvers\src")
import annual_ic as A
from ratio_engine.spec import load_ratio_set
from ratio_engine.calc import compute_ratios_for_ticker
from ratio_engine.scoring import RatioObservation, score_universe

cache=json.load(open(A.CACHE,encoding="utf-8"))
rs=load_ratio_set(os.path.join(A.REPO,"config","ratios.v2.json"),
                  os.path.join(A.REPO,"config","ratio_fields.v2.json"))
tickers={t:r for t,r in cache.items() if r.get("currency")=="TRY"}
from datetime import date
SCHED=[(date(2022,12,31),date(2023,3,16)),(date(2023,12,31),date(2024,3,15)),
       (date(2024,12,31),date(2025,3,16)),(date(2025,12,31),date(2026,3,16))]
K=10
def med(v): 
    v=sorted(v); return v[len(v)//2] if len(v)%2 else (v[len(v)//2-1]+v[len(v)//2])/2
acc={"value":[], "quality":[]}
for ye,t0 in SCHED:
    obs,grp,fwd={},{},{}
    obs=[]
    for tk,rec in tickers.items():
        if ye.isoformat() not in rec["years"]: continue
        p0=A.price_on(rec["prices"],t0); p1=A.price_on(rec["prices"],t0+timedelta(days=182))
        if not p0 or not p1 or p0<=0: continue
        rows=A.synth_rows(rec["years"],ye,t0)
        try: outs=compute_ratios_for_ticker(tk,rows,rs,rec["group"],{(tk,t0):p0})
        except Exception: continue
        for o in outs:
            if o.period_end==ye: obs.append(RatioObservation(tk,o.ratio_name,o.value,o.status))
        grp[tk]=rec["group"]; fwd[tk]=p1/p0-1.0
    res=score_universe(rs,obs,grp)
    uni=med(list(fwd.values()))
    print(f"\n### {t0} -> {t0+timedelta(days=182)} | evren medyan {uni:+.1%}")
    for comp in ("value","quality"):
        rows=[(r.composites[comp].score,tk) for tk,r in res.items()
              if r.composites.get(comp) and r.composites[comp].score is not None]
        if len(rows)<2*K: continue
        rows.sort(reverse=True)
        top=[fwd[tk] for _,tk in rows[:K]]; bot=[fwd[tk] for _,tk in rows[-K:]]
        sp=med(top)-med(bot); acc[comp].append(sp)
        print(f"  {comp:8} ilk{K} medyan {med(top):+7.1%} | son{K} medyan {med(bot):+7.1%}"
              f" | fark {sp:+7.1%}  (ilk10: {', '.join(tk for _,tk in rows[:K][:5])}...)")
print("\n" + "="*60)
for comp,v in acc.items():
    if v: print(f"{comp:8} 4 yil ortalama fark: {sum(v)/len(v):+.1%}  "
                f"(yillar: {', '.join(f'{x:+.0%}' for x in v)})")
