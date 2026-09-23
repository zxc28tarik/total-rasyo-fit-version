"""The static ledger must cover all scored definitions without invented IC."""
import json

from research.tr2.legacy_inventory import OUTPUT, RATIOS, inventory


def test_legacy_inventory_covers_exactly_the_scored_ratios():
    generated = inventory()
    definitions = json.loads(RATIOS.read_text())["ratios"]
    expected = {name for name, spec in definitions.items() if spec.get("role") != "INTERMEDIATE"}
    actual = {row["ratio_name"] for row in generated["ratios"]}
    assert len(actual) == len(expected) == 67
    assert actual == expected
    assert [row["ratio_name"] for row in generated["ratios"]] == sorted(expected)


def test_inventory_does_not_invent_research_or_a_keep_decision():
    generated = inventory()
    assert all(row["decision"] is None and row["univariate_forward_ic"] is None
               and row["pit_safety"] is None for row in generated["ratios"])
    assert json.loads(OUTPUT.read_text(encoding="utf-8")) == generated
