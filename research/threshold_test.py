"""Does raising the bar help?

The top-ten rule buys ten names whatever they score.  This compares that
against absolute thresholds: hold everything scoring above the bar on BOTH
composites, equally weighted, rebalanced monthly.  If the engine's score means
anything, a higher bar should pay better.
"""
import json, os, sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import annual_ic as A
import backtest as B
from ratio_engine.spec import load_ratio_set
from ratio_engine.calc import compute_ratios_for_ticker
from ratio_engine.scoring import RatioObservation, score_universe

BARS = [0.50, 0.55, 0.60, 0.65]
EVERY = int(os.environ.get("HOLD_MONTHS", "1"))

qc = json.load(open(B.QUARTERLY, encoding="utf-8"))
ac = json.load(open(B.ANNUAL, encoding="utf-8"))
rs = load_ratio_set(os.path.join(A.REPO, "config", "ratios.v2.json"),
                    os.path.join(A.REPO, "config", "ratio_fields.v2.json"))

tickers = {t for t, r in qc.items() if r.get("currency") == "TRY"} & set(ac)
series = {t: B.build_quarters(qc[t], ac[t]) for t in tickers}
prices = {t: {**ac[t]["prices"], **qc[t]["prices"]} for t in tickers}
groups = {t: qc[t]["group"] for t in tickers}
dates = B.month_ends(date(2025, 9, 30), date(2026, 9, 23))
dates = dates[::EVERY]
if dates[-1] < date(2026, 9, 23):
    dates = dates + [date(2026, 9, 23)]

eq = {b: 1.0 for b in BARS}
eq["top10"] = 1.0
eq["evren"] = 1.0
rows = []

for i, t0 in enumerate(dates[:-1]):
    t1 = dates[i + 1]
    obs, group_of, ret = [], {}, {}
    for tk in tickers:
        qs = series[tk]
        pub = [pe for pe in qs if B.available_on(pe, t0)]
        if not pub:
            continue
        latest = max(pub)
        p0, p1 = A.price_on(prices[tk], t0), A.price_on(prices[tk], t1)
        if not p0 or not p1 or p0 <= 0:
            continue
        r = [{**f, "period_end": pe, "version_tag": "ORIGINAL", "t0_date": t0}
             for pe, f in qs.items() if pe <= latest]
        try:
            outs = compute_ratios_for_ticker(tk, r, rs, groups[tk], {(tk, t0): p0})
        except Exception:
            continue
        hit = [o for o in outs if o.period_end == latest]
        if not hit:
            continue
        for o in hit:
            obs.append(RatioObservation(tk, o.ratio_name, o.value, o.status))
        group_of[tk] = groups[tk]
        ret[tk] = p1 / p0 - 1.0

    if not obs:
        continue
    res = score_universe(rs, obs, group_of)
    sc = {}
    for tk, r in res.items():
        v, q = r.composites.get("value"), r.composites.get("quality")
        if v and v.score is not None and q and q.score is not None and tk in ret:
            sc[tk] = (v.score, q.score)
    if len(sc) < 20:
        continue

    def rk(idx):
        order = sorted(sc, key=lambda t: -sc[t][idx])
        return {t: p for p, t in enumerate(order, 1)}

    rv, rq = rk(0), rk(1)
    top10 = sorted(sc, key=lambda t: ((rv[t] + rq[t]) / 2.0, t))[:10]

    line = [str(t0)]
    for b in BARS:
        names = [t for t, (v, q) in sc.items() if v > b and q > b]
        if names:
            r = sum(ret[t] for t in names) / len(names)
            eq[b] *= (1 + r)
            line.append(f"{len(names):>3} {r:>+7.1%}")
        else:
            line.append(f"{0:>3} {'nakit':>7}")
    r10 = sum(ret[t] for t in top10) / len(top10)
    ru = sum(ret.values()) / len(ret)
    eq["top10"] *= (1 + r10)
    eq["evren"] *= (1 + ru)
    line += [f"{r10:>+7.1%}", f"{ru:>+7.1%}"]
    rows.append(line)

head = f"{'tarih':12}" + "".join(f"{'>' + str(b):>13}" for b in BARS)
head += f"{'ilk10':>9}{'evren':>9}"
print(head)
for line in rows:
    print(f"{line[0]:12}" + "".join(f"{c:>13}" for c in line[1:1 + len(BARS)])
          + f"{line[-2]:>9}{line[-1]:>9}")

print("")
print("=" * 74)
print(f"12 AY TOPLAM GETIRI | elde tutma {EVERY} ay | maliyet haric")
for b in BARS:
    print(f"  esik >{b:.2f} : {eq[b] - 1:+.1%}")
print(f"  ilk 10     : {eq['top10'] - 1:+.1%}")
print(f"  EVREN      : {eq['evren'] - 1:+.1%}")
