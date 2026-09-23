"""Create an honest, deterministic static inventory of the legacy ratio set.

This is an audit starting point, not a recommendation to retain any ratio.
Empirical fields and decisions remain null until PIT data and tests exist.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RATIOS = ROOT / "config" / "ratios.v2.json"
FIELDS = ROOT / "config" / "ratio_fields.v2.json"
OUTPUT = ROOT / "research" / "tr2" / "legacy_ratio_inventory.json"

# These are formula-level dispositions only. They do not select a TR2 feature;
# forward PIT tests may instead reject it entirely. Exact source expressions
# are checked so a later legacy edit forces the finding to be reviewed again.
FORMULA_FINDINGS = {
    "REVENUE_CAGR_3Y": {
        "source_formula": "(revenue / lag(revenue, 12)) - 1",
        "finding": "Three-year total change is labelled CAGR; annualizing exponent 1/3 is absent. Revenue 100 to 200 yields 100% here versus about 25.99% annual CAGR.",
    },
    "EBITDA_YOY_GROWTH": {
        "source_formula": "(EBITDA_TTM - (lag(ebit, 4) + lag(depreciation_amortization, 4))) / abs(lag(ebit, 4) + lag(depreciation_amortization, 4))",
        "finding": "Current trailing-four-quarter EBITDA is compared with one quarter four quarters ago, not the prior trailing-four-quarter EBITDA. Unit/time windows differ.",
    },
    "FCF_YOY_GROWTH": {
        "source_formula": "(FCF_TTM - (lag(cfo, 4) - abs(lag(capex, 4)))) / abs(lag(cfo, 4) - abs(lag(capex, 4)))",
        "finding": "Current trailing-four-quarter FCF is compared with one quarter four quarters ago, not prior trailing-four-quarter FCF. Unit/time windows differ.",
    },
}


def inventory(ratios_path: Path = RATIOS, fields_path: Path = FIELDS) -> dict:
    ratio_config = json.loads(ratios_path.read_text(encoding="utf-8"))
    field_config = json.loads(fields_path.read_text(encoding="utf-8"))
    fields = field_config["fields"]
    scored = ratio_config["ratios"]
    rows = []
    for ratio_name, definition in sorted(scored.items()):
        if definition.get("role") == "INTERMEDIATE":
            continue
        required = definition["requires"]
        missing_fields = sorted(set(required) - fields.keys())
        if missing_fields:
            raise ValueError(f"{ratio_name}: unknown fields {missing_fields}")
        finding = FORMULA_FINDINGS.get(ratio_name)
        if finding and finding["source_formula"] != definition["formula"]:
            raise ValueError(f"{ratio_name}: source formula changed; re-audit the finding")
        rows.append({
            "ratio_name": ratio_name,
            "formula": definition["formula"],
            "direction": definition["direction"],
            "sector_applicability": sorted(definition["applies_to"]),
            "required_fields": required,
            "field_semantics": {name: {"tier": fields[name]["tier"], "flow": fields[name]["flow"]}
                                for name in required},
            "family_legacy": definition["family"],
            "domain_legacy": definition["domain"],
            "out_of_domain_legacy": definition["out_of_domain"],
            "anchor_legacy": definition.get("anchor"),
            "economic_thesis": None,
            "formula_correctness": finding["finding"] if finding else None,
            "period_semantics_review": None,
            "pit_safety": None,
            "inflation_sensitivity": None,
            "accounting_caveats": None,
            "outlier_behavior": None,
            "coverage": None,
            "redundancy_cluster": None,
            "univariate_forward_ic": None,
            "rolling_ic": None,
            "incremental_ic": None,
            "decision": "REWRITE" if finding else None,
            "reason": "Incorrect legacy formula; TR2 inclusion still requires PIT OOS evidence" if finding else None,
        })
    return {
        "status": "STATIC_INVENTORY_ONLY",
        "source": {
            "ratios_path": str(ratios_path.relative_to(ROOT)),
            "ratios_sha256": hashlib.sha256(ratios_path.read_bytes()).hexdigest(),
            "fields_path": str(fields_path.relative_to(ROOT)),
            "fields_sha256": hashlib.sha256(fields_path.read_bytes()).hexdigest(),
        },
        "scored_ratio_count": len(rows),
        "ratios": rows,
    }


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(inventory(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
