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
