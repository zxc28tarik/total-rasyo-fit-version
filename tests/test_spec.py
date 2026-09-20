"""The v2 loader must reject a malformed ratio set loudly, not warn.

67 ratio definitions cannot be reviewed by eye, so every consistency rule the
design depends on is enforced at load time.  Each test here corresponds to a
class of silent misconfiguration that v1 could not detect - most importantly the
sector-applicability drift that let BANK end up with 10 eligible ratios against
NONFIN's 26 without anyone noticing.
"""
from __future__ import annotations

import pytest

from ratio_engine.spec import RatioSpecError, load_ratio_set, coverage_report, load_field_registry
from tests._fixtures import build_set, real_set, simple_ratio


FAMILIES = {"FAM_A": "P1", "FAM_B": "P2"}
SHARES = {"P1": 0.5, "P2": 0.5}
COMPOSITES = {"c1": ["P1", "P2"]}
GROUPS = ["G1"]


def _build(tmp_path, ratios, **kw):
    return build_set(tmp_path, ratios, families=FAMILIES, groups=GROUPS,
                     pillar_shares=SHARES, composites=COMPOSITES, **kw)


def test_real_set_loads_with_expected_shape():
    rs = real_set()
    assert len(rs.scored()) == 67
    assert len(rs.intermediates()) == 9
    assert len({s.family for s in rs.scored()}) == 19
    assert set(rs.composites()) == {"quality", "growth", "value"}


def test_real_set_coverage_report_counts_the_ingestion_backlog():
    rs = real_set()
    report = coverage_report(rs, load_field_registry("config/ratio_fields.v2.json"))
    nonfin = report["NONFIN"]
    assert nonfin["applicable"] == 67
    # Every applicable ratio is either computable now or blocked by a named tier.
    assert 0 < nonfin["computable_today"] < nonfin["applicable"]
    assert nonfin["blocked_by_tier"]


def test_unknown_field_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="alan kaydinda olmayan"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS, field="a") | {"requires": ["nope"]}})


def test_unknown_family_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="olmayan aile"):
        _build(tmp_path, {"R1": simple_ratio("FAM_MISSING", GROUPS)})


def test_unknown_sector_group_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="bilinmeyen grup"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", ["G_NOPE"])})


def test_disallowed_function_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="izin verilmeyen fonksiyon"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS) | {"formula": "eval(a)"}})


def test_formula_reading_an_undefined_name_is_rejected(tmp_path):
    """Intermediates must be declared before their dependants, not by dict luck."""
    with pytest.raises(RatioSpecError, match="tanimsiz"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS) | {"formula": "LATER + a"}})


def test_anchor_must_agree_with_direction(tmp_path):
    with pytest.raises(RatioSpecError, match="HIGHER_BETTER"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS) | {"anchor": {"weak": 5, "strong": 1}}})


def test_band_ratio_cannot_carry_an_anchor(tmp_path):
    with pytest.raises(RatioSpecError, match="anchor tasiyamaz"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS) | {
            "direction": "BAND", "band": {"low": 1, "high": 2}, "anchor": {"weak": 1, "strong": 2}}})


def test_group_with_no_applicable_ratio_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="uygulanabilir degil"):
        build_set(tmp_path, {"R1": simple_ratio("FAM_A", ["G1"])},
                  families=FAMILIES, groups=["G1", "G2"],
                  pillar_shares=SHARES, composites=COMPOSITES)


def test_pillar_in_two_composites_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="birden fazla kompozitte"):
        build_set(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS)},
                  families=FAMILIES, groups=GROUPS, pillar_shares=SHARES,
                  composites={"c1": ["P1", "P2"], "c2": ["P1"]})


def test_pillar_missing_from_every_composite_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="hicbir kompozite girmeyen"):
        build_set(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS)},
                  families=FAMILIES, groups=GROUPS, pillar_shares=SHARES,
                  composites={"c1": ["P1"]})


def test_composite_with_no_live_pillar_for_a_group_is_rejected(tmp_path):
    """A group whose composite has only zero-share pillars would score
    YETERSIZ_KAPSAM forever, silently. The loader refuses instead."""
    with pytest.raises(RatioSpecError, match="payi sifirdan buyuk"):
        build_set(
            tmp_path,
            {"R1": simple_ratio("FAM_A", GROUPS), "R2": simple_ratio("FAM_B", GROUPS, field="b")},
            families=FAMILIES, groups=GROUPS, pillar_shares=SHARES,
            composites={"c1": ["P1"], "c2": ["P2"]},
            by_group={"G1": {"P1": 1.0, "P2": 0.0}},
        )
