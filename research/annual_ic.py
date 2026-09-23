"""Multi-period 6-month rank-IC from annual statements.

The engine wants quarters.  We have years.  So each fiscal year is expanded
into four synthetic quarters:

  FLOW fields  (revenue, net income, cfo, ...)  ->  annual / 4 in each quarter,
      so sum4q() at the year end reproduces the annual figure EXACTLY.
  POINT fields (assets, equity, shares, ...)    ->  the year-end balance in
      each quarter, so avg() returns the year-end value.

What this buys: every trailing-twelve-month ratio becomes computable and
correct at fiscal year ends, and year-on-year growth works off real prior-year
figures.  What it costs: intra-year shape is invented, so avg() is a year-end
reading rather than a true average, and nothing here can say anything about
within-year seasonality.  Ratios are only ever read at fiscal year ends, where
the trailing sums are exact.

Windows are one per fiscal year and do not overlap, so the per-year ICs are
independent and can be averaged with a t-statistic.
"""
import json, os, sys
from datetime import date, timedelta

sys.path.insert(0, r"C:\Users\zxc28\Desktop\totalrasyofitvers\src")

from ratio_engine.spec import load_ratio_set
from ratio_engine.calc import compute_ratios_for_ticker
from ratio_engine.scoring import RatioObservation, score_universe

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"C:\Users\zxc28\Desktop\totalrasyofitvers"
CACHE = os.path.join(HERE, "bist_annual.json")

LAG_DAYS = 75          # annual report published within ~75 days of year end
FORWARD_DAYS = 182     # six months
MIN_NAMES = 12         # below this a cross-section is not worth correlating

POINT = {
    "total_assets", "total_equity", "current_assets", "current_liabilities",
    "cash_and_eq", "st_investments", "receivables", "inventory", "debt_st",
    "debt_lt", "shares_out", "shares_diluted", "accounts_payable", "net_ppe",
    "intangibles_goodwill", "lease_liabilities", "minority_interest",
}


def d(s):
    y, m, dd = (int(x) for x in s.split("-"))
    return date(y, m, dd)


def price_on(prices, when, back=14):
    for i in range(back + 1):
        k = str(when - timedelta(days=i))
        if k in prices:
            return prices[k]
    return None


def quarter_ends(year_end):
    """The four quarter ends of the fiscal year ending at `year_end`."""
    out = []
    y, m = year_end.year, year_end.month
    for back in (9, 6, 3, 0):
        mm = m - back
        yy = y
        if mm <= 0:
            mm += 12
            yy -= 1
        out.append(date(yy, 12, 31) if mm == 12
                   else date(yy, mm + 1, 1) - timedelta(days=1))
    return out


def synth_rows(years, upto, t0):
    """Expand every fiscal year at or before `upto` into four quarters."""
    rows = []
    for ye_s, fields in years.items():
        ye = d(ye_s)
        if ye > upto:
            continue
        for qe in quarter_ends(ye):
            row = {"period_end": qe, "version_tag": "ORIGINAL", "t0_date": t0}
            for f, v in fields.items():
                row[f] = v if f in POINT else v / 4.0
            rows.append(row)
    return rows


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return None if dx == 0 or dy == 0 else num / (dx * dy)


def main():
    cache = json.load(open(CACHE, encoding="utf-8"))
    rs = load_ratio_set(os.path.join(REPO, "config", "ratios.v2.json"),
                        os.path.join(REPO, "config", "ratio_fields.v2.json"))
    tickers = {t: r for t, r in cache.items() if r.get("currency") == "TRY"}

    year_ends = sorted({ye for r in tickers.values() for ye in r["years"]})
    today = date.today()
    schedule = []
    for ye_s in year_ends:
        ye = d(ye_s)
        t0 = ye + timedelta(days=LAG_DAYS)
        if t0 + timedelta(days=FORWARD_DAYS) > today:
            continue
        # A year with only a balance sheet cannot feed a single flow ratio.
        with_income = sum(1 for r in tickers.values()
                          if "revenue" in r["years"].get(ye_s, {}))
        if with_income < MIN_NAMES:
            print(f"  {ye} atlandi: gelir tablosu olan {with_income} hisse")
            continue
        schedule.append((ye, t0))

    print(f"evren {len(cache)} cekildi, {len(tickers)} TRY")
    print(f"olcum tarihleri: {[str(t0) for _, t0 in schedule]}\n")

    per_date = {}
    for year_end, t0 in schedule:
        obs, group_of, fwd = [], {}, {}
        tally = {}
        for tk, rec in tickers.items():
            if year_end.isoformat() not in rec["years"]:
                continue
            p0 = price_on(rec["prices"], t0)
            p1 = price_on(rec["prices"], t0 + timedelta(days=FORWARD_DAYS))
            if not p0 or not p1 or p0 <= 0:
                continue
            rows = synth_rows(rec["years"], year_end, t0)
            if not rows:
                continue
            try:
                outs = compute_ratios_for_ticker(tk, rows, rs, rec["group"],
                                                 {(tk, t0): p0})
            except Exception:
                continue
            for o in outs:
                if o.period_end != year_end:
                    continue
                obs.append(RatioObservation(tk, o.ratio_name, o.value, o.status))
                tally[o.status] = tally.get(o.status, 0) + 1
            group_of[tk] = rec["group"]
            fwd[tk] = p1 / p0 - 1.0

        if not obs:
            continue
        results = score_universe(rs, obs, group_of)
        rets = sorted(fwd.values())
        med = rets[len(rets) // 2] if rets else 0.0

        print("=" * 70)
        print(f"MALI YIL {year_end} | skor {t0} -> {t0 + timedelta(days=FORWARD_DAYS)}"
              f" | {len(group_of)} hisse | evren medyan getiri {med:+.1%}")
        print(f"  rasyo sonuclari: {tally}")

        for comp in ("quality", "growth", "value"):
            xs, ys = [], []
            for tk, res in results.items():
                c = res.composites.get(comp)
                if c is None or c.score is None:
                    continue
                xs.append(c.score)
                ys.append(fwd[tk])
            ic = spearman(xs, ys) if len(xs) >= MIN_NAMES else None
            if ic is None:
                print(f"  {comp:8} n={len(xs):3}  IC=olculemedi")
            else:
                se = (1.0 / (len(xs) - 1)) ** 0.5
                print(f"  {comp:8} n={len(xs):3}  IC={ic:+.3f}  (+-{se:.3f})")
                per_date.setdefault(comp, []).append((str(t0), ic, len(xs)))
        print()

    print("=" * 70)
    print("DONEMLER ARASI ORTALAMA (pencereler cakismiyor, bagimsiz)")
    for comp, vals in per_date.items():
        ics = [v[1] for v in vals]
        k = len(ics)
        mean = sum(ics) / k
        if k > 1:
            sd = (sum((v - mean) ** 2 for v in ics) / (k - 1)) ** 0.5
            t = mean / (sd / k ** 0.5) if sd > 0 else float("nan")
            print(f"  {comp:8} ortalama IC={mean:+.3f}  k={k} donem  "
                  f"sd={sd:.3f}  t={t:+.2f}")
        else:
            print(f"  {comp:8} ortalama IC={mean:+.3f}  k=1 donem (t hesaplanamaz)")
        for t0s, ic, n in vals:
            print(f"      {t0s}  IC={ic:+.3f}  n={n}")


if __name__ == "__main__":
    main()
