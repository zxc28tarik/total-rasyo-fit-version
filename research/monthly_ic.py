"""Monthly-rebalanced 6-month rank-IC, with the overlap corrected for.

The annual run measured four cross-sections because fundamentals update once a
year.  But a composite is not fundamentals alone - every valuation multiple
carries the price, and the price moves daily.  So each month is a genuinely
different cross-section, built from the newest filing that was public at the
time, and there are about forty of them rather than four.

The cost is that consecutive months share most of their forward window: a
6-month return sampled monthly overlaps five times over.  Averaging the ICs is
still unbiased, but the naive standard error is far too small, so the
t-statistic here is Newey-West corrected with five lags.  Both are printed,
because the gap between them is the point.
"""
import json, os, sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import annual_ic as A
from ratio_engine.spec import load_ratio_set
from ratio_engine.calc import compute_ratios_for_ticker
from ratio_engine.scoring import RatioObservation, score_universe

LAG_DAYS = 75
FORWARD_DAYS = 182
MIN_NAMES = 20
NW_LAGS = 5          # a 6-month window sampled monthly overlaps 5 times


def month_starts(first, last):
    out, y, m = [], first.year, first.month
    while date(y, m, 15) <= last:
        out.append(date(y, m, 15))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def newey_west_t(series, lags=NW_LAGS):
    """t of the mean, with autocovariance up to `lags` folded in (Bartlett)."""
    n = len(series)
    if n < 3:
        return None, None
    mean = sum(series) / n
    dev = [x - mean for x in series]
    gamma0 = sum(d * d for d in dev) / n
    var = gamma0
    for j in range(1, min(lags, n - 1) + 1):
        gj = sum(dev[i] * dev[i - j] for i in range(j, n)) / n
        var += 2.0 * (1.0 - j / (lags + 1.0)) * gj
    var = max(var, 1e-12)
    naive = mean / ((gamma0 / n) ** 0.5) if gamma0 > 0 else None
    return mean / ((var / n) ** 0.5), naive


def main():
    cache = json.load(open(A.CACHE, encoding="utf-8"))
    rs = load_ratio_set(os.path.join(A.REPO, "config", "ratios.v2.json"),
                        os.path.join(A.REPO, "config", "ratio_fields.v2.json"))
    tickers = {t: r for t, r in cache.items() if r.get("currency") == "TRY"}

    # Only fiscal years that actually carry an income statement can be used.
    usable_years = sorted({
        ye for ye in {y for r in tickers.values() for y in r["years"]}
        if sum(1 for r in tickers.values()
               if "revenue" in r["years"].get(ye, {})) >= MIN_NAMES
    })
    first = A.d(usable_years[0]) + timedelta(days=LAG_DAYS)
    last = date.today() - timedelta(days=FORWARD_DAYS)
    dates = month_starts(first, last)
    print(f"{len(tickers)} hisse | {len(dates)} aylik kesit "
          f"({dates[0]} -> {dates[-1]})\n")

    series = {"quality": [], "growth": [], "value": []}
    keep = {}
    rows_out = []

    for t0 in dates:
        # The newest filing that was public on t0.
        known = [A.d(y) for y in usable_years if A.d(y) + timedelta(days=LAG_DAYS) <= t0]
        if not known:
            continue
        year_end = max(known)

        obs, group_of, fwd = [], {}, {}
        for tk, rec in tickers.items():
            if year_end.isoformat() not in rec["years"]:
                continue
            p0 = A.price_on(rec["prices"], t0)
            p1 = A.price_on(rec["prices"], t0 + timedelta(days=FORWARD_DAYS))
            if not p0 or not p1 or p0 <= 0:
                continue
            rows = A.synth_rows(rec["years"], year_end, t0)
            try:
                outs = compute_ratios_for_ticker(tk, rows, rs, rec["group"],
                                                 {(tk, t0): p0})
            except Exception:
                continue
            got = False
            for o in outs:
                if o.period_end == year_end:
                    obs.append(RatioObservation(tk, o.ratio_name, o.value, o.status))
                    got = True
            if not got:
                continue
            group_of[tk] = rec["group"]
            fwd[tk] = p1 / p0 - 1.0

        if len(group_of) < MIN_NAMES:
            continue
        results = score_universe(rs, obs, group_of)

        line = [str(t0), str(year_end), str(len(group_of))]
        for comp in ("quality", "growth", "value"):
            xs = [(r.composites[comp].score, fwd[tk])
                  for tk, r in results.items()
                  if r.composites.get(comp) and r.composites[comp].score is not None]
            if len(xs) < MIN_NAMES:
                line.append("   -  ")
                continue
            ic = A.spearman([a for a, _ in xs], [b for _, b in xs])
            if ic is None:
                line.append("   -  ")
                continue
            series[comp].append(ic)
            line.append(f"{ic:+.3f}")
        rows_out.append(line)

    print(f"{'tarih':12}{'bilanco':12}{'n':>4}  {'quality':>8}{'growth':>8}{'value':>8}")
    for line in rows_out:
        print(f"{line[0]:12}{line[1]:12}{line[2]:>4}  "
              f"{line[3]:>8}{line[4]:>8}{line[5]:>8}")

    print("\n" + "=" * 62)
    print("ORTALAMA IC (aylik kesitler, 6 aylik ileri getiri)")
    print(f"{'kompozit':10}{'k':>4}{'ortIC':>9}{'sd':>8}{'t_naif':>9}"
          f"{'t_NW':>8}{'poz%':>7}")
    for comp, vals in series.items():
        k = len(vals)
        if k < 3:
            print(f"{comp:10}{k:>4}  yetersiz")
            continue
        mean = sum(vals) / k
        sd = (sum((v - mean) ** 2 for v in vals) / (k - 1)) ** 0.5
        t_nw, t_naive = newey_west_t(vals)
        pos = 100.0 * sum(1 for v in vals if v > 0) / k
        print(f"{comp:10}{k:>4}{mean:>+9.3f}{sd:>8.3f}"
              f"{(t_naive if t_naive is not None else float('nan')):>+9.2f}"
              f"{(t_nw if t_nw is not None else float('nan')):>+8.2f}{pos:>6.0f}%")
        keep[comp] = vals

    print(chr(10) + "GECIKME DUYARLILIGI (t_NW)")
    print("  5 = getiri cakismasi | 11-17 = bilanconun 12 ay sabit kalmasi")
    print(f"{'kompozit':10}" + "".join(f"L={L:<6}" for L in (0, 5, 11, 17, 23)))
    for comp, vals in keep.items():
        cells = []
        for L in (0, 5, 11, 17, 23):
            if L == 0:
                _, tn = newey_west_t(vals, lags=1)
                cells.append(f"{tn:+.2f}   " if tn else "  -    ")
            else:
                tw, _ = newey_west_t(vals, lags=L)
                cells.append(f"{tw:+.2f}   " if tw else "  -    ")
        print(f"{comp:10}" + "".join(cells))

    if False:
        pass

    print("\nt_naif cakismayi yok sayar ve anlamliligi ABARTIR.")
    print(f"t_NW {NW_LAGS} gecikmeli Newey-West duzeltmesidir; bakilacak olan odur.")
    print("|t| >= 2 kabaca %5 anlamlilik.")


if __name__ == "__main__":
    main()
