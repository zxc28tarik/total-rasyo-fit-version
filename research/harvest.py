"""Pull real BIST quarterly statements + prices from yfinance into a cache.

Deliberately dumb: fetch, map field names, write JSON.  No ratio logic here.
"""
import json, os, sys, time
from datetime import date

import yfinance as yf

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_cache.json")

BANKS = "AKBNK GARAN ISCTR YKBNK VAKBN HALKB TSKB ALBRK SKBNK ICBCT QNBTR".split()
INSURANCE = "ANSGR AGESA TURSG RAYSG ANHYT".split()
HOLDING = "KCHOL SAHOL ALARK AGHOL GLYHO DOHOL GSDHO IHLAS NTHOL BRYAT IEYHO".split()
FINANCIAL = "ISMEN GLBMD OYAKC ISFIN GARFA".split()

UNIVERSE = """
AEFES AKBNK AKCNS AKFGY AKSA AKSEN ALARK ALBRK ALFAS ANSGR ARCLK ASELS ASTOR
AYDEM AYGAZ BERA BIENY BIMAS BRSAN BRYAT BUCIM CANTE CCOLA CEMTS CIMSA CWENE
DOAS DOHOL ECILC ECZYT EGEEN EKGYO ENERY ENJSA ENKAI EREGL EUPWR FROTO GARAN
GESAN GLYHO GUBRF GWIND HALKB HEKTS IPEKE ISCTR ISDMR ISGYO ISMEN IZMDC KARSN
KCHOL KLSER KONTR KONYA KORDS KOZAA KOZAL KRDMD MAVI MGROS MIATK ODAS OTKAR
OYAKC PENTA PETKM PGSUS QUAGR SAHOL SASA SAYAS SISE SKBNK SMRTG SOKM TAVHL
TCELL THYAO TKFEN TOASO TRGYO TSKB TTKOM TTRAK TUKAS TUPRS TURSG ULKER VAKBN
VESBE VESTL YEOTK YKBNK YYLGD ZOREN
""".split()

INC = {
    "revenue": ["Total Revenue", "Operating Revenue"],
    "cogs": ["Cost Of Revenue", "Reconciled Cost Of Revenue"],
    "gross_profit": ["Gross Profit"],
    "ebit": ["EBIT", "Operating Income", "Total Operating Income As Reported"],
    "net_income": ["Net Income", "Net Income Common Stockholders"],
    "interest_exp": ["Interest Expense", "Interest Expense Non Operating"],
    "pretax_income": ["Pretax Income"],
    "tax_expense": ["Tax Provision"],
    "shares_diluted": ["Diluted Average Shares", "Basic Average Shares"],
}
BAL = {
    "total_assets": ["Total Assets"],
    "total_equity": ["Stockholders Equity", "Common Stock Equity",
                     "Total Equity Gross Minority Interest"],
    "current_assets": ["Current Assets"],
    "current_liabilities": ["Current Liabilities"],
    "cash_and_eq": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
    "st_investments": ["Other Short Term Investments", "Available For Sale Securities"],
    "receivables": ["Accounts Receivable", "Gross Accounts Receivable", "Other Receivables"],
    "inventory": ["Inventory"],
    "debt_st": ["Current Debt", "Current Debt And Capital Lease Obligation"],
    "debt_lt": ["Long Term Debt", "Long Term Debt And Capital Lease Obligation"],
    "shares_out": ["Ordinary Shares Number", "Share Issued"],
    "accounts_payable": ["Accounts Payable", "Payables"],
    "net_ppe": ["Net PPE"],
    "intangibles_goodwill": ["Goodwill And Other Intangible Assets", "Goodwill"],
    "lease_liabilities": ["Capital Lease Obligations", "Long Term Capital Lease Obligation"],
    "minority_interest": ["Minority Interest"],
}
CF = {
    "cfo": ["Operating Cash Flow"],
    "capex": ["Capital Expenditure", "Purchase Of PPE"],
    "depreciation_amortization": ["Depreciation And Amortization", "Depreciation"],
    "dividends_paid": ["Cash Dividends Paid"],
}
# Fields yfinance signs the other way round from the ratio set (sign=POSITIVE).
ABS_FIELDS = {"dividends_paid", "interest_exp", "depreciation_amortization",
              "accounts_payable", "cogs"}


def group_of(t):
    if t in BANKS:
        return "BANK"
    if t in INSURANCE:
        return "INSURANCE"
    if t in HOLDING:
        return "HOLDING"
    if t in FINANCIAL:
        return "FINANCIAL"
    if t.endswith("GYO") or t in ("EKGYO", "ISGYO", "TRGYO", "AKFGY"):
        return "GYO"
    return "NONFIN"


def pick(df, labels):
    if df is None or df.empty:
        return {}
    for lab in labels:
        if lab in df.index:
            return {str(c.date()): df.loc[lab, c] for c in df.columns}
    return {}


def harvest(ticker):
    tk = yf.Ticker(ticker + ".IS")
    inc, bal, cf = tk.quarterly_income_stmt, tk.quarterly_balance_sheet, tk.quarterly_cashflow
    if bal is None or bal.empty:
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
                if field in ABS_FIELDS:
                    v = abs(v)
                per.setdefault(pe, {})[field] = v

    try:
        cur = (tk.info or {}).get("financialCurrency")
    except Exception:
        cur = None

    hist = tk.history(period="2y", interval="1d", auto_adjust=False)
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
            "periods": per, "prices": prices}


def main():
    cache = {}
    if os.path.exists(OUT):
        cache = json.load(open(OUT, encoding="utf-8"))
    todo = [t for t in UNIVERSE if t not in cache]
    print(f"{len(cache)} onbellekte, {len(todo)} cekilecek", flush=True)

    for i, t in enumerate(todo, 1):
        try:
            rec = harvest(t)
        except Exception as exc:
            print(f"  {t}: HATA {type(exc).__name__}: {exc}", flush=True)
            rec = None
        if rec:
            cache[t] = rec
            print(f"[{i}/{len(todo)}] {t} {rec['group']:9} {str(rec['currency']):4} "
                  f"{len(rec['periods'])} donem, {len(rec['prices'])} fiyat", flush=True)
        else:
            print(f"[{i}/{len(todo)}] {t} BOS", flush=True)
        if i % 10 == 0:
            json.dump(cache, open(OUT, "w", encoding="utf-8"))
        time.sleep(1.2)

    json.dump(cache, open(OUT, "w", encoding="utf-8"))
    print(f"\nBITTI: {len(cache)} hisse -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
