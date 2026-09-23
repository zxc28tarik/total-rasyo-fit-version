"""The static ledger must cover all scored definitions without invented IC."""
import json

import pytest

from research.tr2.legacy_inventory import FORMULA_FINDINGS, OUTPUT, RATIOS, inventory


def test_legacy_inventory_covers_exactly_the_scored_ratios():
    generated = inventory()
    definitions = json.loads(RATIOS.read_text())["ratios"]
    expected = {name for name, spec in definitions.items() if spec.get("role") != "INTERMEDIATE"}
    actual = {row["ratio_name"] for row in generated["ratios"]}
    assert len(actual) == len(expected) == 67
    assert actual == expected
    assert [row["ratio_name"] for row in generated["ratios"]] == sorted(expected)


def test_inventory_does_not_invent_empirical_research_or_a_keep_decision():
    generated = inventory()
    assert all(row["decision"] in (None, "REWRITE") and row["univariate_forward_ic"] is None
               and row["pit_safety"] is None for row in generated["ratios"])
    assert {row["ratio_name"] for row in generated["ratios"] if row["decision"] == "REWRITE"} == set(FORMULA_FINDINGS)
    assert json.loads(OUTPUT.read_text(encoding="utf-8")) == generated


def test_formula_findings_fail_if_source_formula_changes(tmp_path):
    source = json.loads(RATIOS.read_text())
    source["ratios"]["REVENUE_CAGR_3Y"]["formula"] = "(revenue / lag(revenue, 12)) ** (1/3) - 1"
    changed = tmp_path / "ratios.json"
    changed.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="re-audit"):
        inventory(changed)
