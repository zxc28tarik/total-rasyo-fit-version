"""Shared builders for the v2 ratio-layer tests.

The structural tests need ratio sets whose shape they control (how many ratios
sit in a family, which groups a ratio applies to).  Building those from JSON on
disk keeps them going through the real loader, so a test can never assert
against a set the validator would have rejected.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from ratio_engine.calc import RatioOutcome
from ratio_engine.spec import load_ratio_set


REAL_RATIOS = "config/ratios.v2.json"
REAL_FIELDS = "config/ratio_fields.v2.json"


def real_set():
    return load_ratio_set(REAL_RATIOS, REAL_FIELDS)


def write_registry(tmp_path: Path, fields: dict[str, str] | None = None) -> Path:
    fields = fields or {"a": "CURRENT", "b": "CURRENT", "c": "CURRENT", "d": "CURRENT"}
    path = tmp_path / "fields.json"
    path.write_text(json.dumps({
        "meta": {"field_set_version": "test"},
        "fields": {k: {"tier": v, "flow": "PERIOD"} for k, v in fields.items()},
    }), encoding="utf-8")
    return path


def build_set(
    tmp_path: Path,
    ratios: dict,
    *,
    families: dict[str, str],
    groups: list[str],
    pillar_shares: dict[str, float],
    composites: dict[str, list[str]],
    by_group: dict | None = None,
    name: str = "ratios.json",
    fields: dict[str, str] | None = None,
):
    ratios_path = tmp_path / name
    ratios_path.write_text(json.dumps({
        "meta": {
            "ratio_set_version": "test",
            "field_set_version": "test",
            "sector_groups": groups,
            "families": families,
            "composites": composites,
            "pillar_shares": {"default": pillar_shares, "by_group": by_group or {}},
        },
        "ratios": ratios,
    }), encoding="utf-8")
    return load_ratio_set(ratios_path, write_registry(tmp_path, fields))


def simple_ratio(family: str, groups: list[str], field: str = "a", **extra) -> dict:
    spec = {
        "family": family,
        "direction": "HIGHER_BETTER",
        "formula": field,
        "requires": [field],
        "domain": [],
        "out_of_domain": "MISSING",
        "applies_to": groups,
    }
    spec.update(extra)
    return spec


def _quarter_end_from_index(q_index: int) -> date:
    year, quarter = divmod(q_index, 4)
    month = quarter * 3 + 3
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def rising_roe_outcomes(ticker="AAA", n=8, start=0.10, step=0.01):
    """n quarters of ROE rising by `step` each quarter, ending 2025-12-31."""
    end_index = 2025 * 4 + 3
    return [
        RatioOutcome(
            ticker=ticker,
            period_end=_quarter_end_from_index(end_index - (n - 1 - i)),
            version_tag="ORIGINAL",
            ratio_name="ROE",
            value=start + i * step,
            status="OK",
        )
        for i in range(n)
    ]
