import pytest

from ratio_engine.trend import TrendTriple, TrendError


def test_ok_triple_carries_three_finite_numbers():
    t = TrendTriple(
        ratio_name="ROE", level=0.20, slope=0.004, stability=0.01,
        status="OK", quarters_used=8,
    )
    assert t.level == 0.20
    assert t.slope == 0.004
    assert t.stability == 0.01


def test_missing_triple_carries_no_numbers():
    t = TrendTriple(
        ratio_name="ROE", level=None, slope=None, stability=None,
        status="MISSING", quarters_used=3,
    )
    assert t.level is None


def test_ok_status_with_null_component_is_rejected():
    with pytest.raises(TrendError):
        TrendTriple(
            ratio_name="ROE", level=0.20, slope=None, stability=0.01,
            status="OK", quarters_used=8,
        )


def test_missing_status_with_a_number_is_rejected():
    with pytest.raises(TrendError):
        TrendTriple(
            ratio_name="ROE", level=0.20, slope=0.004, stability=0.01,
            status="MISSING", quarters_used=3,
        )


from ratio_engine.trend import _ols_slope


def test_slope_of_a_perfect_line_is_its_gradient():
    points = [(0, 1.0), (1, 1.5), (2, 2.0), (3, 2.5)]
    assert _ols_slope(points) == pytest.approx(0.5)


def test_slope_of_a_flat_series_is_zero():
    points = [(0, 2.0), (1, 2.0), (2, 2.0), (3, 2.0)]
    assert _ols_slope(points) == pytest.approx(0.0)


def test_gap_in_quarters_does_not_steepen_the_slope():
    # Q0=1.0, Q1=1.5, Q2 missing, Q3=2.5.  Index-aware fitting must read this
    # as the same 0.5/quarter line, not 0.75 across three consecutive points.
    points = [(0, 1.0), (1, 1.5), (3, 2.5)]
    assert _ols_slope(points) == pytest.approx(0.5)


def test_slope_needs_two_distinct_x_values():
    assert _ols_slope([(2, 1.0)]) is None
    assert _ols_slope([(2, 1.0), (2, 3.0)]) is None


from ratio_engine.trend import _residual_mad


def test_perfect_line_has_zero_residual_spread():
    points = [(0, 1.0), (1, 1.5), (2, 2.0), (3, 2.5)]
    assert _residual_mad(points, slope=0.5) == pytest.approx(0.0)


def test_noisy_series_has_larger_spread_than_clean_one():
    clean = [(0, 1.0), (1, 1.1), (2, 1.2), (3, 1.3)]
    noisy = [(0, 1.0), (1, 2.0), (2, 0.5), (3, 1.3)]
    assert _residual_mad(noisy, slope=0.1) > _residual_mad(clean, slope=0.1)


def test_residual_spread_is_never_negative():
    points = [(0, -5.0), (1, 3.0), (2, -2.0)]
    assert _residual_mad(points, slope=0.0) >= 0.0


from datetime import date

from ratio_engine.calc import RatioOutcome
from ratio_engine.trend import compute_trend
from tests._fixtures import rising_roe_outcomes


def test_rising_series_yields_positive_slope_and_latest_level():
    t = compute_trend(rising_roe_outcomes(), "ROE", date(2025, 12, 31))
    assert t.status == "OK"
    assert t.quarters_used == 8
    assert t.slope == pytest.approx(0.01)
    assert t.level == pytest.approx(0.17)
    assert t.stability == pytest.approx(0.0)


def test_too_few_quarters_is_missing_not_zero():
    t = compute_trend(rising_roe_outcomes(n=5), "ROE", date(2025, 12, 31))
    assert t.status == "MISSING"
    assert t.slope is None
    assert t.quarters_used == 5


def test_non_ok_quarters_do_not_count_toward_the_minimum():
    outcomes = rising_roe_outcomes()
    # Blank three quarters out as BEST: they carry no number, so they are not
    # observations (K21), leaving five - one short of the minimum.
    blanked = [
        RatioOutcome(ticker=o.ticker, period_end=o.period_end,
                     version_tag=o.version_tag, ratio_name=o.ratio_name,
                     value=None, status="BEST")
        for o in outcomes[:3]
    ]
    t = compute_trend(blanked + outcomes[3:], "ROE", date(2025, 12, 31))
    assert t.status == "MISSING"
    assert t.quarters_used == 5


def test_quarters_outside_the_window_are_ignored():
    t = compute_trend(rising_roe_outcomes(n=12), "ROE", date(2025, 12, 31))
    assert t.quarters_used == 8


def test_a_window_without_the_end_quarter_has_no_level():
    outcomes = rising_roe_outcomes(n=9)[:-1]
    t = compute_trend(outcomes, "ROE", date(2025, 12, 31))
    assert t.status == "MISSING"


def test_unknown_ratio_is_missing():
    t = compute_trend(rising_roe_outcomes(), "NO_SUCH_RATIO", date(2025, 12, 31))
    assert t.status == "MISSING"
    assert t.quarters_used == 0


def test_public_surface_exports_the_new_primitives():
    import ratio_engine

    assert ratio_engine.compute_trend is not None
    assert ratio_engine.TrendTriple is not None
    assert ratio_engine.adv_try is not None
    assert "compute_trend" in ratio_engine.__all__
    assert "adv_try" in ratio_engine.__all__
