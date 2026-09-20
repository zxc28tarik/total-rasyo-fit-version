"""Three outcomes where v1 had one boolean.

The defect being fixed was measured on the live v1 code: a debt-free company
has no interest expense, INTEREST_COVERAGE went NA, the NaN propagated through
rsc_scoring._wmean and wiped rsc_core_norm entirely, and run_daily_pipeline then
filled the NaN M1 with 0.0.  The company scored zero on quality for having no
debt.  These tests pin the distinction that prevents it.
"""
from __future__ import annotations

from datetime import date

import pytest

from ratio_engine.calc import (
    STATUS_BEST, STATUS_MISSING, STATUS_NOT_APPLICABLE, STATUS_OK, STATUS_WORST,
    RatioCalcV2Error, RatioOutcome, compute_ratios_for_ticker, status_summary,
)
from tests._fixtures import real_set


QUARTERS = [date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30), date(2025, 12, 31),
            date(2026, 3, 31), date(2026, 6, 30), date(2026, 9, 30), date(2026, 12, 31)]


def _rows(**overrides):
    rows = []
    for i, pe in enumerate(QUARTERS):
        row = dict(
            period_end=pe, version_tag="ORIGINAL", t0_date=pe,
            revenue=1000.0 + 50 * i, cogs=400.0 + 20 * i, gross_profit=None,
            ebit=200.0 + 10 * i, net_income=150.0 + 8 * i, interest_exp=20.0,
            cfo=180.0 + 9 * i, capex=-30.0,
            total_assets=5000.0, total_equity=4000.0, current_assets=2000.0,
            current_liabilities=500.0, cash_and_eq=900.0, st_investments=100.0,
            receivables=300.0, inventory=250.0, debt_st=200.0, debt_lt=300.0,
            shares_out=1000.0, shares_diluted=1000.0,
        )
        row.update(overrides)
        rows.append(row)
    return rows


def _latest(ticker="X", group="NONFIN", **overrides):
    rs = real_set()
    rows = _rows(**overrides)
    out = compute_ratios_for_ticker(
        ticker, rows, rs, group, {(ticker, pe): 20.0 for pe in QUARTERS}
    )
    return {o.ratio_name: o for o in out if o.period_end == QUARTERS[-1]}


def test_debt_free_company_gets_best_not_missing():
    """The exact v1 failure: no interest expense is perfect coverage, not a gap."""
    latest = _latest(interest_exp=0.0, debt_st=0.0, debt_lt=0.0)
    assert latest["INTEREST_COVERAGE"].status == STATUS_BEST
    assert latest["CFO_TO_TOTAL_DEBT"].status == STATUS_BEST
    assert latest["ST_DEBT_RATIO"].status == STATUS_BEST


def test_service_business_without_inventory_is_not_applicable():
    latest = _latest(inventory=0.0)
    assert latest["DIO_DAYS"].status == STATUS_NOT_APPLICABLE


def test_loss_making_company_is_worst_on_pe_not_cheap():
    """An undefined multiple must not let a loss-maker rank as cheap."""
    latest = _latest(net_income=-100.0)
    assert latest["PE_TTM"].status == STATUS_WORST


def test_uningested_field_is_missing_not_zero():
    """depreciation_amortization is KAP_XBRL tier and not populated yet."""
    latest = _latest()
    assert latest["EV_EBITDA"].status == STATUS_MISSING
    assert latest["EV_EBITDA"].value is None
    assert latest["DPO_DAYS"].status == STATUS_MISSING


def test_ratio_outside_its_sector_is_not_applicable():
    latest = _latest(group="BANK")
    # DSO_DAYS applies only to NONFIN.
    assert latest["DSO_DAYS"].status == STATUS_NOT_APPLICABLE


def test_ordinary_company_computes_ok_values():
    latest = _latest()
    for name in ("CURRENT_RATIO", "ROE", "PE_TTM", "INTEREST_COVERAGE", "DIO_DAYS"):
        assert latest[name].status == STATUS_OK, name
        assert latest[name].value is not None


def test_intermediates_never_emit_outcome_rows():
    rs = real_set()
    latest = _latest()
    for spec in rs.intermediates():
        assert spec.name not in latest


def test_failed_intermediate_makes_dependants_missing_not_substituted():
    """EBITDA_TTM cannot form without D&A, so EV_EBITDA is MISSING - never a
    silently substituted EV/EBIT."""
    latest = _latest()
    assert latest["EV_EBITDA"].status == STATUS_MISSING
    assert latest["EV_EBIT"].status == STATUS_OK  # the substitute exists separately


def test_every_scored_ratio_gets_exactly_one_outcome_per_period():
    rs = real_set()
    rows = _rows()
    out = compute_ratios_for_ticker("X", rows, rs, "NONFIN", {("X", pe): 20.0 for pe in QUARTERS})
    per_period = [o for o in out if o.period_end == QUARTERS[-1]]
    assert len(per_period) == len(rs.scored())
    assert len({o.ratio_name for o in per_period}) == len(rs.scored())


def test_status_counts_sum_to_the_scored_set():
    rs = real_set()
    latest = _latest()
    assert sum(status_summary(latest.values()).values()) == len(rs.scored())


def test_outcome_rejects_ok_without_value():
    with pytest.raises(RatioCalcV2Error):
        RatioOutcome("X", QUARTERS[0], "ORIGINAL", "ROE", None, STATUS_OK)


def test_outcome_rejects_non_ok_carrying_a_value():
    """A value under a status that says nothing was measured is a fabrication."""
    with pytest.raises(RatioCalcV2Error):
        RatioOutcome("X", QUARTERS[0], "ORIGINAL", "ROE", 0.5, STATUS_MISSING)


def test_unknown_sector_group_is_rejected():
    rs = real_set()
    with pytest.raises(RatioCalcV2Error):
        compute_ratios_for_ticker("X", _rows(), rs, "NO_SUCH_GROUP", {})
