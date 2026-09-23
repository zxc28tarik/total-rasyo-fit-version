"""Drive the whole chain on real BIST data and print the board.

    annual statements -> synthetic quarters -> ratios -> composites
        -> two engines -> ranks -> consensus / divergence

Run research/harvest_annual.py first to fill the cache.
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
from ratio_engine.trend import compute_trend
from engines.saf_deger import SafDeger
from engines.kalite_bilesik import KaliteBilesik
from board.comparison import build_board
from board.report import render_csv, render_lists, render_table

RAW_COLUMNS = ["PE_TTM", "PB", "EV_EBITDA", "NET_DEBT_TO_EBITDA", "DIVIDEND_YIELD"]
STABILITY_RATIO = "CFO_MARGIN"   # K25


def stability_scores(trends):
    """Turn residual MADs into 0..1, low spread = high score.

    A plain rank inversion, not the median/MAD machinery: that lives in the
    scoring layer and is driven by a ratio spec, and the triple is not a ratio
    (K8).  Wiring the triple into score_universe properly is Faz 3.
    """
    got = {t: v for t, v in trends.items() if v is not None}
    if len(got) < 2:
        return {}
    order = sorted(got, key=lambda t: got[t])          # smallest MAD first
    n = len(order) - 1
    return {t: 1.0 - i / n for i, t in enumerate(order)}


def main():
    cache = json.load(open(A.CACHE, encoding="utf-8"))
    rs = load_ratio_set(os.path.join(A.REPO, "config", "ratios.v2.json"),
                        os.path.join(A.REPO, "config", "ratio_fields.v2.json"))
    tickers = {t: r for t, r in cache.items() if r.get("currency") == "TRY"}

    # The most widely shared fiscal year end, not the latest: a single company
    # on a January year end would otherwise define the whole board.
    counts = {}
    for r in tickers.values():
        for ye in r["years"]:
            counts[ye] = counts.get(ye, 0) + 1
    newest = max(counts)
    year_end = A.d(max((ye for ye in counts if counts[ye] >= 0.5 * len(tickers)),
                       default=newest))
    t0 = year_end + timedelta(days=A.LAG_DAYS)

    obs, group_of, raw, trends = [], {}, {}, {}
    for tk, rec in tickers.items():
        if year_end.isoformat() not in rec["years"]:
            continue
        p0 = A.price_on(rec["prices"], t0)
        if not p0:
            continue
        rows = A.synth_rows(rec["years"], year_end, t0)
        try:
            outs = compute_ratios_for_ticker(tk, rows, rs, rec["group"], {(tk, t0): p0})
        except Exception:
            continue

        latest = [o for o in outs if o.period_end == year_end]
        if not latest:
            continue
        for o in latest:
            obs.append(RatioObservation(tk, o.ratio_name, o.value, o.status))
        raw[tk] = {o.ratio_name: o.value for o in latest if o.ratio_name in RAW_COLUMNS}

        triple = compute_trend(outs, STABILITY_RATIO, year_end)
        trends[tk] = triple.stability if triple.status == "OK" else None
        group_of[tk] = rec["group"]

    universe = score_universe(rs, obs, group_of)
    stab = stability_scores(trends)

    results = {
        "saf_deger": SafDeger().run(universe),
        "kalite": KaliteBilesik(stability=stab).run(universe),
    }
    board = build_board(results, raw=raw)

    print(f"TOTAL RASYO TAHTASI | mali yil {year_end} | skor tarihi {t0}")
    print(f"{len(universe)} hisse skorlandi | istikrar okunan {len(stab)}\n")
    print(render_table(board, raw_columns=RAW_COLUMNS))
    print(render_lists(board, top_n=10))

    out = os.path.join(HERE, "board.csv")
    open(out, "w", encoding="utf-8").write(render_csv(board, RAW_COLUMNS))
    print(f"CSV -> {out}")


if __name__ == "__main__":
    main()
