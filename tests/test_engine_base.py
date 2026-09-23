"""What every engine hands back, and how gates bite.

The board ranks engines side by side, so engines may differ in what they weigh
but not in the shape of what they return.  These tests pin that shape and the
one arithmetic rule that keeps value traps off the top of the list: gates
multiply (K15).
"""
from __future__ import annotations

import pytest

from engines.base import EngineError, EngineResult, apply_gates, weigh_axes


def test_ok_result_carries_a_finite_score():
    r = EngineResult(engine="saf_deger", ticker="AAA", score=0.82, status="OK",
                     axes={"value": 0.82}, gates={}, coverage=0.75, notes=())
    assert r.score == 0.82


def test_missing_result_carries_no_score():
    r = EngineResult(engine="saf_deger", ticker="AAA", score=None,
                     status="MISSING", axes={}, gates={}, coverage=0.10,
                     notes=("kapsam esigin altinda",))
    assert r.score is None


def test_ok_status_without_a_score_is_rejected():
    with pytest.raises(EngineError):
        EngineResult(engine="e", ticker="AAA", score=None, status="OK",
                     axes={}, gates={}, coverage=0.5, notes=())


def test_missing_status_with_a_score_is_rejected():
    with pytest.raises(EngineError):
        EngineResult(engine="e", ticker="AAA", score=0.5, status="MISSING",
                     axes={}, gates={}, coverage=0.5, notes=())


def test_unknown_status_is_rejected():
    with pytest.raises(EngineError):
        EngineResult(engine="e", ticker="AAA", score=0.5, status="FINE",
                     axes={}, gates={}, coverage=0.5, notes=())


def test_gated_result_keeps_its_score_so_the_board_can_show_why():
    """A gate that multiplies to zero is a verdict, not a gap."""
    r = EngineResult(engine="e", ticker="AAA", score=0.0, status="GATED",
                     axes={"value": 0.9}, gates={"G_muhasebe": 0.0},
                     coverage=0.8, notes=("G_muhasebe veto",))
    assert r.status == "GATED"
    assert r.axes["value"] == 0.9


def test_coverage_outside_zero_one_is_rejected():
    with pytest.raises(EngineError):
        EngineResult(engine="e", ticker="AAA", score=0.5, status="OK",
                     axes={}, gates={}, coverage=1.4, notes=())


def test_gates_multiply_rather_than_add():
    score, applied, status = apply_gates(0.80, {"a": 0.5, "b": 0.5})
    assert score == pytest.approx(0.20)
    assert applied == {"a": 0.5, "b": 0.5}
    assert status == "OK"


def test_a_zero_gate_marks_the_result_gated():
    score, _, status = apply_gates(0.90, {"G_muhasebe": 0.0})
    assert score == pytest.approx(0.0)
    assert status == "GATED"


def test_no_gates_leaves_the_score_untouched():
    score, applied, status = apply_gates(0.65, {})
    assert score == pytest.approx(0.65)
    assert applied == {}
    assert status == "OK"


def test_a_cheap_value_cannot_buy_its_way_past_a_veto():
    """K15, the value-trap guard.  Addition would have let it."""
    cheap_and_vetoed, _, _ = apply_gates(1.00, {"G_muhasebe": 0.0})
    dear_and_clean, _, _ = apply_gates(0.40, {"G_muhasebe": 1.0})
    assert cheap_and_vetoed < dear_and_clean


def test_axes_are_weighed_as_declared():
    assert weigh_axes({"a": 1.0, "b": 0.0}, {"a": 0.7, "b": 0.3}) == pytest.approx(0.7)


def test_a_missing_axis_is_refused_rather_than_renormalised():
    """K24.  Silently spreading a lost axis's weight would make two companies
    carry differently defined scores into the same ranking."""
    with pytest.raises(EngineError):
        weigh_axes({"a": 1.0}, {"a": 0.7, "b": 0.3})
