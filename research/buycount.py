"""How many names the engine rated positively each month, and what the ten it
bought actually scored.

The buy rule in backtest.py is relative - top ten by average rank - so it
always buys exactly ten whatever the scores look like.  This script prints the
scores behind that choice so the rule can be judged rather than assumed.
"""
import json, os, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import annual_ic as A
import backtest as B
from ratio_engine.spec import load_ratio_set
from ratio_engine.calc import compute_ratios_for_ticker
from ratio_engine.scoring import RatioObservation, score_universe

qc = json.load(open(B.QUARTERLY, encoding="utf-8"))
ac = json.load(open(B.ANNUAL, encoding="utf-8"))
rs = load_ratio_set(os.path.join(A.REPO, "config", "ratios.v2.json"),
                    os.path.join(A.REPO, "config", "ratio_fields.v2.json"))

tickers = {t for t, r in qc.items() if r.get("currency") == "TRY"} & set(ac)
series = {t: B.build_quarters(qc[t], ac[t]) for t in tickers}
prices = {t: {**ac[t]["prices"], **qc[t]["prices"]} for t in tickers}
groups = {t: qc[t]["group"] for t in tickers}
dates = B.month_ends(date(2025, 9, 30), date(2026, 9, 23))

summary = []

for t0 in dates:
    obs, group_of = [], {}
    for tk in tickers:
        qs = series[tk]
        pub = [pe for pe in qs if B.available_on(pe, t0)]
        if not pub:
            continue
        latest = max(pub)
        p0 = A.price_on(prices[tk], t0)
        if not p0:
            continue
        rows = [{**f, "period_end": pe, "version_tag": "ORIGINAL", "t0_date": t0}
                for pe, f in qs.items() if pe <= latest]
        try:
            outs = compute_ratios_for_ticker(tk, rows, rs, groups[tk], {(tk, t0): p0})
        except Exception:
            continue
        hit = [o for o in outs if o.period_end == latest]
        if not hit:
            continue
        for o in hit:
            obs.append(RatioObservation(tk, o.ratio_name, o.value, o.status))
        group_of[tk] = groups[tk]

    if not obs:
        continue
    res = score_universe(rs, obs, group_of)

    sc = {}
    for tk, r in res.items():
        v, q = r.composites.get("value"), r.composites.get("quality")
        if v and v.score is not None and q and q.score is not None:
            sc[tk] = (v.score, q.score)
    if len(sc) < 20:
        continue

    def rk(i):
        order = sorted(sc, key=lambda t: -sc[t][i])
        return {t: p for p, t in enumerate(order, 1)}

    rv, rq = rk(0), rk(1)
    picks = sorted(sc, key=lambda t: ((rv[t] + rq[t]) / 2.0, t))[:10]

    print("")
    print(f"{t0}  aldiklarim")
    print(f"   {'hisse':8}{'deger':>8}{'kalite':>8}{'ortalama':>10}")
    for t in picks:
        v, q = sc[t]
        print(f"   {t:8}{v:>8.3f}{q:>8.3f}{(v + q) / 2:>10.3f}")

    port = sum((sc[t][0] + sc[t][1]) / 2 for t in picks) / len(picks)
    uni = sum((v + q) / 2 for v, q in sc.values()) / len(sc)
    best = max((v + q) / 2 for v, q in sc.values())
    print(f"   {'PORTFOY':8}{'':8}{'':8}{port:>10.3f}"
          f"   (evren ort {uni:.3f} | evrenin en iyisi {best:.3f})")

    c5 = sum(1 for v, q in sc.values() if v > 0.5 and q > 0.5)
    c6 = sum(1 for v, q in sc.values() if v > 0.6 and q > 0.6)
    c7 = sum(1 for v, q in sc.values() if v > 0.7 and q > 0.7)
    summary.append((t0, len(group_of), len(sc), c5, c6, c7, port, uni, best))

print("")
print("=" * 78)
print(f"{'tarih':12}{'evren':>6}{'skor':>6}{'>.5':>5}{'>.6':>5}{'>.7':>5}"
      f"{'portfoy':>10}{'evrenOrt':>10}{'enIyi':>8}")
for (t0, n, k, c5, c6, c7, port, uni, best) in summary:
    print(f"{str(t0):12}{n:>6}{k:>6}{c5:>5}{c6:>5}{c7:>5}"
          f"{port:>10.3f}{uni:>10.3f}{best:>8.3f}")

if summary:
    m = len(summary)
    print("")
    print(f"  12 ay ortalamasi: portfoy {sum(r[6] for r in summary)/m:.3f}"
          f" | evren {sum(r[7] for r in summary)/m:.3f}"
          f" | evrenin en iyisi {sum(r[8] for r in summary)/m:.3f}")
