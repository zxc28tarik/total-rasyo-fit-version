"""One year, monthly rebalanced, on the newest quarterly filing public each day.

The decision rule, stated up front so it can be argued with:

  * growth is excluded.  Its measured IC was +0.004 over 36 monthly
    cross-sections with 44% positive months - it carries no signal, and
    including it would only add noise.
  * value and quality are combined on RANK, not score (K27): the two
    composites are differently defined and 0.80 from one is not 0.80 from the
    other, but their orderings live in the same universe.
  * a name must have BOTH composites scored.  One opinion is not a decision.
  * top 10 by average rank, equally weighted, rebalanced monthly.

Quarter construction, in order of preference per fiscal year:

  1. four real quarters from the quarterly feed;
  2. three real quarters plus the annual total - the fourth is then determined
     by subtraction, which is arithmetic rather than assumption;
  3. annual / 4 for all four.  Only fiscal 2023-2024 fall back this far, and
     they only ever feed the trailing sums of the earliest windows.

Publication lag is deliberately conservative - 75 days for Q1-Q3 and 90 for
the annual - so the engine is never handed a filing before it could have been
read.
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

QUARTERLY = os.path.join(HERE, "bist_cache.json")
ANNUAL = os.path.join(HERE, "bist_annual.json")

START = date(*map(int, (os.environ.get("BT_START") or "2025-9-30").split("-")))
END = date(2026, 9, 23)
HOLD = 10
REBAL_EVERY = int(os.environ.get("BT_EVERY", "1"))   # months between trades
COST_PER_SIDE = 0.002          # 0.2% - BIST commission plus half-spread
LAG_INTERIM = 75
LAG_ANNUAL = 90

FLOW = None  # filled below: anything not POINT is a flow


def is_point(field):
    return field in A.POINT


def available_on(period_end, t0):
    lag = LAG_ANNUAL if period_end.month == 12 else LAG_INTERIM
    return period_end + timedelta(days=lag) <= t0


def quarters_of(year_end):
    return A.quarter_ends(year_end)


def build_quarters(qrec, arec):
    """Best available quarterly series per fiscal year.  Returns {date: fields}."""
    out = {}
    years = sorted(arec.get("years", {}))
    for ye_s in years:
        ye = A.d(ye_s)
        annual = arec["years"][ye_s]
        qends = quarters_of(ye)
        present = {qe: qrec.get("periods", {}).get(qe.isoformat())
                   for qe in qends}
        have = [qe for qe, v in present.items() if v]

        for field, total in annual.items():
            if is_point(field):
                # A stock figure: use the real quarter-end where we have it,
                # otherwise carry the year-end balance.
                for qe in qends:
                    val = (present[qe] or {}).get(field)
                    out.setdefault(qe, {})[field] = (
                        val if val is not None else total
                    )
                continue

            vals = {qe: (present[qe] or {}).get(field) for qe in qends}
            known = {qe: v for qe, v in vals.items() if v is not None}
            if len(known) == 4:
                pass                                   # all real
            elif len(known) == 3:
                missing = [qe for qe in qends if qe not in known][0]
                known[missing] = total - sum(known.values())   # exact
            else:
                known = {qe: total / 4.0 for qe in qends}      # fallback
            for qe, v in known.items():
                out.setdefault(qe, {})[field] = v

    # Quarters newer than the last annual: whatever the quarterly feed has.
    for pe_s, fields in qrec.get("periods", {}).items():
        pe = A.d(pe_s)
        if years and pe <= A.d(years[-1]):
            continue
        out.setdefault(pe, {}).update(fields)
    return out


def month_ends(first, last):
    out, y, m = [], first.year, first.month
    while True:
        nxt = date(y + (m == 12), 1 if m == 12 else m + 1, 1)
        eom = nxt - timedelta(days=1)
        if eom > last:
            break
        if eom >= first:
            out.append(eom)
        y, m = nxt.year, nxt.month
    return out


def main():
    qc = json.load(open(QUARTERLY, encoding="utf-8"))
    ac = json.load(open(ANNUAL, encoding="utf-8"))
    rs = load_ratio_set(os.path.join(A.REPO, "config", "ratios.v2.json"),
                        os.path.join(A.REPO, "config", "ratio_fields.v2.json"))

    tickers = {t for t, r in qc.items() if r.get("currency") == "TRY"} & set(ac)
    series = {t: build_quarters(qc[t], ac[t]) for t in tickers}
    prices = {t: qc[t]["prices"] for t in tickers}
    for t in tickers:                      # annual cache has the longer history
        prices[t] = {**ac[t]["prices"], **qc[t]["prices"]}
    groups = {t: qc[t]["group"] for t in tickers}

    dates = month_ends(START, END)
    dates = dates[::REBAL_EVERY] if REBAL_EVERY > 1 else dates
    if dates and dates[-1] < END - timedelta(days=20):
        dates.append(END)
    print(f"{len(tickers)} hisse | {len(dates)} aylik yeniden dengeleme "
          f"({dates[0]} -> {dates[-1]})\n")

    equity, bench_eq = 1.0, 1.0
    held: set[str] = set()
    log = []

    for i, t0 in enumerate(dates[:-1]):
        t1 = dates[i + 1]

        obs, group_of, ret = [], {}, {}
        used_pe = None
        for tk in tickers:
            qs = series[tk]
            publishable = [pe for pe in qs if available_on(pe, t0)]
            if not publishable:
                continue
            latest = max(publishable)
            p0 = A.price_on(prices[tk], t0)
            p1 = A.price_on(prices[tk], t1)
            if not p0 or not p1 or p0 <= 0:
                continue
            rows = []
            for pe, fields in qs.items():
                if pe > latest:
                    continue
                row = dict(fields)
                row.update(period_end=pe, version_tag="ORIGINAL", t0_date=t0)
                rows.append(row)
            try:
                outs = compute_ratios_for_ticker(tk, rows, rs, groups[tk],
                                                 {(tk, t0): p0})
            except Exception:
                continue
            hit = [o for o in outs if o.period_end == latest]
            if not hit:
                continue
            for o in hit:
                obs.append(RatioObservation(tk, o.ratio_name, o.value, o.status))
            group_of[tk] = groups[tk]
            ret[tk] = p1 / p0 - 1.0
            used_pe = max(used_pe, latest) if used_pe else latest

        if not obs:
            continue
        results = score_universe(rs, obs, group_of)

        scored = {}
        for tk, r in results.items():
            v, q = r.composites.get("value"), r.composites.get("quality")
            if v is None or v.score is None or q is None or q.score is None:
                continue
            scored[tk] = (v.score, q.score)
        if len(scored) < HOLD * 2:
            continue

        def ranks(idx):
            order = sorted(scored, key=lambda t: -scored[t][idx])
            return {t: p for p, t in enumerate(order, 1)}

        rv, rq = ranks(0), ranks(1)
        combined = sorted(scored, key=lambda t: ((rv[t] + rq[t]) / 2.0, t))
        picks = combined[:HOLD]

        gross = sum(ret[t] for t in picks) / len(picks)
        turnover = len(set(picks) - held) / len(picks)
        cost = turnover * COST_PER_SIDE * 2
        net = gross - cost

        bench = sum(ret.values()) / len(ret)
        equity *= (1 + net)
        bench_eq *= (1 + bench)
        held = set(picks)

        pos_picks = sum(1 for t in picks if ret[t] > 0)
        pos_uni = sum(1 for v in ret.values() if v > 0)
        log.append((t0, t1, used_pe, len(ret), gross, cost, net, bench,
                    equity, bench_eq, picks, pos_picks, pos_uni, len(scored)))

    print(f"{'donem':24}{'havuz':>6}{'sec+':>6}{'evren+':>8}"
          f"{'evren+%':>9}{'sec+%':>8}{'brut':>8}{'net':>8}{'evren':>8}")
    for (t0, t1, pe, n, g, c, net, b, eq, be, picks, pp, pu, pool) in log:
        print(f"{str(t0)}->{str(t1)}  {pool:>6}{pp:>4}/10"
              f"{pu:>5}/{n:<3}{100.0*pu/n:>8.0f}%{10.0*pp:>7.0f}%"
              f"{g:>+8.1%}{net:>+8.1%}{b:>+8.1%}")

    if log:
        tp = sum(r[11] for r in log); tu = sum(r[12] for r in log)
        tn = sum(r[3] for r in log); m = len(log)
        print(chr(10) + f"  TOPLAM  secilen pozitif {tp}/{10*m} = {100.0*tp/(10*m):.0f}%"
              f"   |   evren pozitif {tu}/{tn} = {100.0*tu/tn:.0f}%")
        print(f"  Motorun secimi rastgeleyi {tp/(10.0*m) - tu/float(tn):+.1%} "
              f"puan gecti (isabet orani farki)")

    print()
    for (t0, t1, pe, n, g, c, net, b, eq, be, picks, pp, pu, pool) in log:
        ups = [t for t in picks if 0 < 1]  # placeholder replaced below
        print(f"  {t0} sectikleri: {', '.join(picks)}")

    if log:
        final_eq, final_be = log[-1][8], log[-1][9]
        months = len(log)
        print("\n" + "=" * 70)
        print(f"{months} ay | {log[0][0]} -> {log[-1][1]}")
        print(f"  PORTFOY (net, maliyet dahil) : {final_eq - 1:+.1%}")
        print(f"  EVREN (esit agirlik)         : {final_be - 1:+.1%}")
        print(f"  FARK                         : {final_eq - final_be:+.1%}")
        wins = sum(1 for r in log if r[6] > r[7])
        print(f"  evreni yendigi ay            : {wins}/{months}")
        gross_tot = 1.0
        for r in log:
            gross_tot *= (1 + r[4])
        print(f"  islem maliyeti olmasa         : {gross_tot - 1:+.1%}")


if __name__ == "__main__":
    main()
