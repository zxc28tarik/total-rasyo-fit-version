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
