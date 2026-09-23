"""Annual statements + long price history.

The quarterly feed had holes and only five quarters, so nothing that needs a
trailing-twelve-month sum could be computed.  Annual statements have no holes
and go back four to five years, which is also what buys us several
non-overlapping measurement windows.
"""
import json, os, time

import yfinance as yf

from harvest import INC, BAL, CF, ABS_FIELDS, UNIVERSE, group_of

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_annual.json")


def pick(df, labels):
    if df is None or df.empty:
        return {}
    for lab in labels:
        if lab in df.index:
            return {str(c.date()): df.loc[lab, c] for c in df.columns}
    return {}


def harvest(ticker):
    tk = yf.Ticker(ticker + ".IS")
    inc, bal, cf = tk.income_stmt, tk.balance_sheet, tk.cashflow
    if bal is None or bal.empty or inc is None or inc.empty:
        return None

    per = {}
    for src, mapping in ((inc, INC), (bal, BAL), (cf, CF)):
        for field, labels in mapping.items():
            for pe, val in pick(src, labels).items():
                try:
                    v = float(val)
                except (TypeError, ValueError):
                    continue
                if v != v:
                    continue
                per.setdefault(pe, {})[field] = abs(v) if field in ABS_FIELDS else v

    try:
        cur = (tk.info or {}).get("financialCurrency")
    except Exception:
        cur = None

    hist = tk.history(period="6y", interval="1d", auto_adjust=False)
    prices = {}
    if hist is not None and not hist.empty:
        for idx, row in hist.iterrows():
            try:
                prices[str(idx.date())] = float(row["Close"])
            except Exception:
                pass
    if not prices:
        return None

    return {"group": group_of(ticker), "currency": cur,
            "years": per, "prices": prices}


def main():
    cache = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    todo = [t for t in UNIVERSE if t not in cache]
    print(f"{len(cache)} onbellekte, {len(todo)} cekilecek", flush=True)

    for i, t in enumerate(todo, 1):
        try:
            rec = harvest(t)
        except Exception as exc:
            print(f"  {t}: HATA {type(exc).__name__}", flush=True)
            rec = None
        if rec:
            cache[t] = rec
            print(f"[{i}/{len(todo)}] {t} {rec['group']:9} {str(rec['currency']):4} "
                  f"{len(rec['years'])} yil, {len(rec['prices'])} fiyat", flush=True)
        else:
            print(f"[{i}/{len(todo)}] {t} BOS", flush=True)
        if i % 10 == 0:
            json.dump(cache, open(OUT, "w", encoding="utf-8"))
        time.sleep(1.2)

    json.dump(cache, open(OUT, "w", encoding="utf-8"))
    print(f"\nBITTI: {len(cache)} hisse -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
