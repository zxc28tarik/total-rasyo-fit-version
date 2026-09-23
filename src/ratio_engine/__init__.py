"""A fail-closed financial ratio engine for Borsa Istanbul.

    spec       ratio-set schema, loaded and validated fail-closed
    calc       formula evaluation into one of five explicit outcomes
    scoring    family-normalised cross-sectional scoring
    evaluator  the safe formula evaluator (vendored, pure stdlib)
    trend      (level, slope, stability) across a window of quarters
    liquidity  average daily turnover, the traded-liquidity gate input
"""
from ratio_engine.spec import (
    RatioSet, RatioSpec, RatioSpecError, coverage_report, load_field_registry,
    load_ratio_set,
)
from ratio_engine.calc import RatioOutcome, compute_ratios_for_ticker, resolve_ratio
from ratio_engine.scoring import (
    CompositeResult, RatioObservation, TickerResult, compute_ratio_weights,
    score_universe,
)
from ratio_engine.trend import TrendError, TrendTriple, compute_trend
from ratio_engine.liquidity import LiquidityResult, adv_try

__all__ = [
    "RatioSet", "RatioSpec", "RatioSpecError", "coverage_report",
    "load_field_registry", "load_ratio_set", "RatioOutcome",
    "compute_ratios_for_ticker", "resolve_ratio", "CompositeResult",
    "RatioObservation", "TickerResult", "compute_ratio_weights",
    "score_universe", "TrendTriple", "TrendError", "compute_trend",
    "LiquidityResult", "adv_try",
]
