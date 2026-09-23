"""The two engines the current ratio set can actually feed.

Total Rasyo v2 and Momentum/Revizyon need a price history this package has no
ingest for, so they are Faz 3.  These two need nothing the engine cannot
already compute.
"""
from __future__ import annotations

import pytest

from engines.kalite_bilesik import KaliteBilesik
from engines.saf_deger import SafDeger
from ratio_engine.scoring import CompositeResult, TickerResult


def _ticker(name, value=None, quality=None, accruals=None, coverage=0.8,
            group="NONFIN"):
    composites = {}
    if value is not None:
        composites["value"] = CompositeResult("OK", value, coverage, 0.5, 8, 10)
    else:
        composites["value"] = CompositeResult("YETERSIZ_KAPSAM", None, 0.1, 0.0, 1, 10)
    if quality is not None:
        composites["quality"] = CompositeResult("OK", quality, coverage, 0.5, 8, 10)
    else:
        composites["quality"] = CompositeResult("YETERSIZ_KAPSAM", None, 0.1, 0.0, 1, 10)
    scores = {} if accruals is None else {"ACCRUALS_TO_ASSETS": accruals}
    return TickerResult(name, group, composites, scores)


# --- Saf Deger ------------------------------------------------------------

def test_the_cheapest_company_scores_highest():
    uni = {"CHEAP": _ticker("CHEAP", value=0.9, accruals=0.9),
           "DEAR": _ticker("DEAR", value=0.2, accruals=0.9)}
    out = SafDeger().run(uni)
    assert out["CHEAP"].score > out["DEAR"].score
    assert out["CHEAP"].status == "OK"


def test_a_company_without_a_value_composite_is_missing_not_zero():
    out = SafDeger().run({"X": _ticker("X", value=None, accruals=0.9)})
    assert out["X"].status == "MISSING"
    assert out["X"].score is None


def test_bad_accruals_gate_the_result():
    uni = {"DODGY": _ticker("DODGY", value=0.95, accruals=0.05)}
    out = SafDeger().run(uni)
    assert out["DODGY"].status == "GATED"
    assert out["DODGY"].score == pytest.approx(0.0)
    assert out["DODGY"].axes["value"] == pytest.approx(0.95)


def test_an_unmeasurable_accruals_ratio_passes_the_gate_but_is_noted():
    """K22.  Refusing to score would mean scoring nobody, because the ratio is
    missing market-wide today.  The compromise is carried in `notes`."""
    out = SafDeger().run({"X": _ticker("X", value=0.6, accruals=None)})
    assert out["X"].status == "OK"
    assert out["X"].gates["G_muhasebe"] == pytest.approx(1.0)
    assert any("G_muhasebe" in n for n in out["X"].notes)


def test_a_vetoed_cheap_company_ranks_below_a_clean_dear_one():
    uni = {"TRAP": _ticker("TRAP", value=1.0, accruals=0.0),
           "CLEAN": _ticker("CLEAN", value=0.3, accruals=0.9)}
    out = SafDeger().run(uni)
    assert out["TRAP"].score < out["CLEAN"].score


# --- Kalite Bilesik -------------------------------------------------------

def test_steady_margins_beat_erratic_ones_at_equal_quality():
    uni = {"STEADY": _ticker("STEADY", quality=0.6, accruals=0.9),
           "ERRATIC": _ticker("ERRATIC", quality=0.6, accruals=0.9)}
    stability = {"STEADY": 0.9, "ERRATIC": 0.1}
    out = KaliteBilesik(stability=stability).run(uni)
    assert out["STEADY"].score > out["ERRATIC"].score


def test_quality_still_dominates_the_blend():
    """0.70 quality against 0.30 stability: a large quality gap must win."""
    uni = {"GOOD": _ticker("GOOD", quality=0.9, accruals=0.9),
           "SHAKY": _ticker("SHAKY", quality=0.2, accruals=0.9)}
    out = KaliteBilesik(stability={"GOOD": 0.0, "SHAKY": 1.0}).run(uni)
    assert out["GOOD"].score > out["SHAKY"].score


def test_without_a_stability_reading_the_engine_is_missing_not_quality_only():
    """K24: the weight of a lost axis is not redistributed."""
    out = KaliteBilesik(stability={}).run(
        {"X": _ticker("X", quality=0.8, accruals=0.9)}
    )
    assert out["X"].status == "MISSING"
    assert out["X"].score is None


def test_without_a_quality_composite_the_engine_is_missing():
    out = KaliteBilesik(stability={"X": 0.5}).run(
        {"X": _ticker("X", quality=None, accruals=0.9)}
    )
    assert out["X"].status == "MISSING"


def test_both_engines_name_themselves_in_their_results():
    uni = {"X": _ticker("X", value=0.5, quality=0.5, accruals=0.9)}
    assert SafDeger().run(uni)["X"].engine == "saf_deger"
    assert KaliteBilesik(stability={"X": 0.5}).run(uni)["X"].engine == "kalite_bilesik"
