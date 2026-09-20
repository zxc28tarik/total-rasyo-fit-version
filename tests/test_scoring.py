"""The eight properties the v2 scoring layer exists to guarantee.

Each maps to a defect measured on the live v1 code:

  1  a single missing ratio wiped the whole score (NaN through _wmean)
  2  a debt-free company therefore scored 0.0 on quality
  3  NA conflated "does not apply" with "not measured"
  4  a pillar's share scaled with its ratio count, so the set could not grow
  5  good_count_ge8 was absolute, capping a bank's ek1 at 10/18 = 0.56
  6  insufficient data surfaced as a silent 0.0 instead of a status
  7  determinate and absent outcomes were indistinguishable
  8  tie handling depended on input order
"""
from __future__ import annotations

import collections

import pytest

from ratio_engine.scoring import (
    RESULT_INSUFFICIENT_COVERAGE, RESULT_OK, RatioObservation, ScoringError,
    compute_ratio_weights, score_universe,
)
from tests._fixtures import build_set, simple_ratio


FAMILIES = {"FAM_A": "P1", "FAM_B": "P1", "FAM_C": "P2"}
SHARES = {"P1": 0.6, "P2": 0.4}
COMPOSITES = {"c1": ["P1", "P2"]}


def _set(tmp_path, ratios, groups=("G1",), by_group=None, name="ratios.json"):
    return build_set(tmp_path, ratios, families=FAMILIES, groups=list(groups),
                     pillar_shares=SHARES, composites=COMPOSITES,
                     by_group=by_group, name=name,
                     fields={"a": "CURRENT", "b": "CURRENT", "c": "CURRENT", "d": "CURRENT"})


def _pool(names, tickers, base=1.0, step=1.0):
    """OK observations with a clean spread so ranking is well defined."""
    obs = []
    for i, t in enumerate(tickers):
        for n in names:
            obs.append(RatioObservation(t, n, base + step * i, "OK"))
    return obs


TICKERS = [f"T{i}" for i in range(1, 7)]


# --- 1 -----------------------------------------------------------------
def test_one_missing_ratio_does_not_wipe_the_score(tmp_path):
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R2": simple_ratio("FAM_B", ["G1"], "b"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    obs = _pool(["R1", "R2", "R3"], TICKERS)
    obs = [o for o in obs if not (o.ticker == "T1" and o.ratio_name == "R3")]
    obs.append(RatioObservation("T1", "R3", None, "MISSING"))

    res = score_universe(rs, obs, {t: "G1" for t in TICKERS})
    c = res["T1"].composites["c1"]
    assert c.status == RESULT_OK
    assert c.score is not None and 0.0 <= c.score <= 1.0
    assert c.coverage < 1.0          # the gap is visible
    assert c.measured == 2 and c.applicable == 3


# --- 2 -----------------------------------------------------------------
def test_determinate_best_is_rewarded_not_penalised(tmp_path):
    """The debt-free company. BEST must beat a mid-pool OK, never equal zero."""
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R2": simple_ratio("FAM_B", ["G1"], "b"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    obs = [o for o in _pool(["R1", "R2", "R3"], TICKERS) if o.ticker != "T1"]
    for n in ("R1", "R2", "R3"):
        obs.append(RatioObservation("T1", n, None, "BEST"))

    res = score_universe(rs, obs, {t: "G1" for t in TICKERS})
    assert res["T1"].composites["c1"].score == pytest.approx(1.0)
    assert res["T1"].composites["c1"].coverage == pytest.approx(1.0)
    assert res["T1"].composites["c1"].good_ratio == pytest.approx(1.0)


# --- 3 -----------------------------------------------------------------
def test_not_applicable_leaves_the_denominator(tmp_path):
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R2": simple_ratio("FAM_B", ["G1"], "b"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    base = _pool(["R1", "R2", "R3"], TICKERS)

    na = [o for o in base if not (o.ticker == "T1" and o.ratio_name == "R3")]
    na.append(RatioObservation("T1", "R3", None, "NOT_APPLICABLE"))
    missing = [o for o in base if not (o.ticker == "T1" and o.ratio_name == "R3")]
    missing.append(RatioObservation("T1", "R3", None, "MISSING"))

    gm = {t: "G1" for t in TICKERS}
    na_res = score_universe(rs, na, gm)["T1"].composites["c1"]
    missing_res = score_universe(rs, missing, gm)["T1"].composites["c1"]

    assert na_res.applicable == 2 and na_res.coverage == pytest.approx(1.0)
    assert missing_res.applicable == 3 and missing_res.coverage < 1.0


# --- 4 -----------------------------------------------------------------
def test_pillar_share_is_independent_of_ratio_count(tmp_path):
    """The property that lets the ratio set grow. In v1 a pillar's real share
    was (ratio count x pillar_w)/sum, so this test would have failed."""
    small = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R9": simple_ratio("FAM_C", ["G1"], "c"),
    }, name="small.json")
    big = _set(tmp_path, {
        **{f"R{i}": simple_ratio("FAM_A", ["G1"], "a") for i in range(1, 8)},
        "R9": simple_ratio("FAM_C", ["G1"], "c"),
    }, name="big.json")

    def pillar_share(rs):
        agg = collections.defaultdict(float)
        for name, w in compute_ratio_weights(rs, "G1", "c1").items():
            agg[rs.specs[name].pillar] += w
        return dict(agg)

    assert pillar_share(small) == pytest.approx(pillar_share(big))
    assert pillar_share(big)["P1"] == pytest.approx(0.6)
    assert sum(compute_ratio_weights(big, "G1", "c1").values()) == pytest.approx(1.0)


def test_families_split_the_pillar_evenly_regardless_of_size(tmp_path):
    rs = _set(tmp_path, {
        "A1": simple_ratio("FAM_A", ["G1"], "a"),
        **{f"B{i}": simple_ratio("FAM_B", ["G1"], "b") for i in range(1, 6)},
        "C1": simple_ratio("FAM_C", ["G1"], "c"),
    })
    w = compute_ratio_weights(rs, "G1", "c1")
    fam = collections.defaultdict(float)
    for name, x in w.items():
        fam[rs.specs[name].family] += x
    # FAM_A and FAM_B share P1's 0.6 evenly even though B has five members.
    assert fam["FAM_A"] == pytest.approx(0.3)
    assert fam["FAM_B"] == pytest.approx(0.3)


# --- 5 -----------------------------------------------------------------
def test_good_ratio_ceiling_is_one_for_every_group(tmp_path):
    """v1's absolute good_count capped a bank at 10/18 = 0.56 while an
    industrial could reach 1.0. A weight share cannot do that."""
    rs = _set(tmp_path, {
        "WIDE1": simple_ratio("FAM_A", ["G_WIDE"], "a"),
        "WIDE2": simple_ratio("FAM_B", ["G_WIDE"], "b"),
        "BOTH": simple_ratio("FAM_C", ["G_WIDE", "G_NARROW"], "c"),
        "NARROW": simple_ratio("FAM_A", ["G_NARROW"], "a"),
    }, groups=("G_WIDE", "G_NARROW"))

    obs = []
    for t in ("W1", "W2"):
        for n in ("WIDE1", "WIDE2", "BOTH"):
            obs.append(RatioObservation(t, n, None, "BEST"))
    for t in ("N1", "N2"):
        for n in ("NARROW", "BOTH"):
            obs.append(RatioObservation(t, n, None, "BEST"))

    res = score_universe(rs, obs, {"W1": "G_WIDE", "W2": "G_WIDE",
                                   "N1": "G_NARROW", "N2": "G_NARROW"})
    wide = res["W1"].composites["c1"]
    narrow = res["N1"].composites["c1"]
    assert wide.applicable == 3 and narrow.applicable == 2
    assert wide.good_ratio == pytest.approx(1.0)
    assert narrow.good_ratio == pytest.approx(1.0)   # no structural ceiling
    assert wide.score == pytest.approx(narrow.score)


# --- 6 -----------------------------------------------------------------
def test_below_coverage_threshold_is_a_status_not_a_silent_zero(tmp_path):
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R2": simple_ratio("FAM_B", ["G1"], "b"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    obs = _pool(["R1", "R2", "R3"], TICKERS)
    obs = [o for o in obs if o.ticker != "T1"]
    obs.append(RatioObservation("T1", "R1", 1.0, "OK"))
    obs.append(RatioObservation("T1", "R2", None, "MISSING"))
    obs.append(RatioObservation("T1", "R3", None, "MISSING"))

    res = score_universe(rs, obs, {t: "G1" for t in TICKERS}, min_coverage=0.5)
    c = res["T1"].composites["c1"]
    assert c.status == RESULT_INSUFFICIENT_COVERAGE
    assert c.score is None          # not 0.0, not NaN
    assert c.coverage < 0.5


# --- 7 -----------------------------------------------------------------
def test_determinate_counts_as_measured_but_missing_does_not(tmp_path):
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R2": simple_ratio("FAM_B", ["G1"], "b"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    gm = {t: "G1" for t in TICKERS}

    def coverage(status):
        obs = [o for o in _pool(["R1", "R2", "R3"], TICKERS) if o.ticker != "T1"]
        obs += [RatioObservation("T1", "R1", 1.0, "OK"),
                RatioObservation("T1", "R2", 1.0, "OK"),
                RatioObservation("T1", "R3", None, status)]
        return score_universe(rs, obs, gm)["T1"].composites["c1"]

    assert coverage("WORST").coverage == pytest.approx(1.0)
    assert coverage("BEST").coverage == pytest.approx(1.0)
    assert coverage("MISSING").coverage < 1.0
    assert coverage("WORST").score < coverage("BEST").score


# --- 8 -----------------------------------------------------------------
def test_tied_values_do_not_depend_on_input_order(tmp_path):
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    gm = {t: "G1" for t in TICKERS}
    obs = [RatioObservation(t, n, 5.0, "OK") for t in TICKERS for n in ("R1", "R3")]

    forward = score_universe(rs, obs, gm)
    backward = score_universe(rs, list(reversed(obs)), gm)
    for t in TICKERS:
        assert forward[t].composites["c1"].score == pytest.approx(
            backward[t].composites["c1"].score
        )


# --- guards -------------------------------------------------------------
def test_unknown_ticker_group_is_rejected(tmp_path):
    rs = _set(tmp_path, {"R1": simple_ratio("FAM_A", ["G1"], "a"),
                         "R3": simple_ratio("FAM_C", ["G1"], "c")})
    with pytest.raises(ScoringError, match="sektor grubu bilinmeyen"):
        score_universe(rs, [RatioObservation("T1", "R1", 1.0, "OK")], {})


def test_observation_outside_the_ratio_set_is_rejected(tmp_path):
    rs = _set(tmp_path, {"R1": simple_ratio("FAM_A", ["G1"], "a"),
                         "R3": simple_ratio("FAM_C", ["G1"], "c")})
    with pytest.raises(ScoringError, match="rasyo setinde olmayan"):
        score_universe(rs, [RatioObservation("T1", "GHOST", 1.0, "OK")], {"T1": "G1"})


def test_ok_observation_requires_a_finite_value():
    with pytest.raises(ScoringError):
        RatioObservation("T1", "R1", None, "OK")


def test_invalid_status_is_rejected():
    with pytest.raises(ScoringError):
        RatioObservation("T1", "R1", 1.0, "WHATEVER")
