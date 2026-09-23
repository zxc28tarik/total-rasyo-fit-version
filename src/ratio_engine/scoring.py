from __future__ import annotations

"""v2 scoring: family-normalised, coverage-explicit, no NaN propagation.

Three v1 defects this replaces, each measured on the live code rather than
inferred:

1. A single missing CORE ratio wiped the whole score.  ``rsc_scoring._wmean``
   summed ``score_1_10`` with numpy, so one NaN made ``rsc_core_norm`` NaN for
   the company; ``run_daily_pipeline`` then filled the NaN M1 with 0.0.

2. A pillar's share of the score scaled with how many ratios it contained,
   because ``_policy_weight`` handed ``pillar_w * ratio_w`` to every ratio and
   ``_wmean`` divided by the weight sum.  Adding ratios silently reweighted,
   which is why the v1 set could not grow.

3. ``good_count_ge8`` was an absolute count against a fixed threshold of 5 and
   ``ek1`` divided by a hardcoded 18.  With 10 eligible ratios a bank could not
   push ``ek1`` past 0.56 and tripped the veto on 50% of its ratios against
   19% for an industrial with 26.

The v2 weight of a ratio, inside one composite, is::

    w = pillar_share / families_applicable(pillar) / ratios_applicable(family)

renormalised so the composite's applicable weights sum to 1.  Adding a ratio to
a family therefore redistributes weight *inside that family only*; the pillar's
share is whatever config says and nothing else.  Coverage is then the weight
actually observed, which turns "how much of this company did we measure" into a
number the rest of the system can read instead of a silence.
"""

from dataclasses import dataclass, field as dc_field
from typing import Iterable, Mapping, Sequence
import math

from ratio_engine.spec import RatioSet, RatioSpec


STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_BEST = "BEST"
STATUS_WORST = "WORST"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
VALID_STATUSES = frozenset(
    {STATUS_OK, STATUS_MISSING, STATUS_BEST, STATUS_WORST, STATUS_NOT_APPLICABLE}
)

RESULT_OK = "OK"
RESULT_INSUFFICIENT_COVERAGE = "YETERSIZ_KAPSAM"

# A determinate out-of-domain outcome is knowledge, not absence: it carries a
# score and counts towards coverage.
DETERMINATE = {STATUS_BEST: 1.0, STATUS_WORST: 0.0}

GOOD_SCORE_THRESHOLD = 0.80
DEFAULT_MIN_COVERAGE = 0.40
DEFAULT_MIN_POOL = 5
ANCHOR_BLEND = 0.40
MAD_SCALE = 1.4826


class ScoringError(ValueError):
    pass


@dataclass(frozen=True)
class RatioObservation:
    ticker: str
    ratio_name: str
    value: float | None
    status: str

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ScoringError(
                f"{self.ticker}/{self.ratio_name}: gecersiz status {self.status!r}"
            )
        if self.status == STATUS_OK and not _is_finite(self.value):
            raise ScoringError(
                f"{self.ticker}/{self.ratio_name}: status OK ise deger sonlu olmali"
            )


@dataclass(frozen=True)
class CompositeResult:
    status: str
    score: float | None
    coverage: float
    good_ratio: float
    measured: int
    applicable: int


@dataclass(frozen=True)
class TickerResult:
    ticker: str
    group: str
    composites: Mapping[str, CompositeResult]
    ratio_scores: Mapping[str, float] = dc_field(default_factory=dict)

    def score(self, composite: str) -> float | None:
        result = self.composites.get(composite)
        return None if result is None else result.score


def _is_finite(value: object) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        out = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(out)


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise ScoringError("medyan bos dizide hesaplanamaz")
    mid = n // 2
    return ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0


def _winsorize(values: Sequence[float], p: float) -> list[float]:
    if p <= 0 or len(values) < 3:
        return list(values)
    ordered = sorted(values)
    lo = ordered[max(0, int(math.floor(p * (len(ordered) - 1))))]
    hi = ordered[min(len(ordered) - 1, int(math.ceil((1 - p) * (len(ordered) - 1))))]
    return [min(max(v, lo), hi) for v in values]


def _transform(spec: RatioSpec, value: float) -> float:
    if spec.transform == "signed_log":
        return math.copysign(math.log1p(abs(value)), value)
    if spec.transform == "clip" and spec.clip is not None:
        return min(max(value, spec.clip["low"]), spec.clip["high"])
    return value


def _orient(spec: RatioSpec, value: float) -> float:
    """Map a transformed value onto a 'higher is better' axis."""
    if spec.direction == "LOWER_BETTER":
        return -value
    if spec.direction == "BAND" and spec.band is not None:
        centre = (spec.band["low"] + spec.band["high"]) / 2.0
        return -abs(value - centre)
    return value


def _band_absolute(spec: RatioSpec, value: float) -> float | None:
    """Absolute score for a BAND ratio: inside the band is good on its own terms."""
    if spec.band is None:
        return None
    low, high = spec.band["low"], spec.band["high"]
    half = (high - low) / 2.0
    if half <= 0:
        return None
    if low <= value <= high:
        return 0.80
    excess = (low - value) if value < low else (value - high)
    return max(0.05, 0.80 - 0.50 * (excess / half))


def _logistic(z: float) -> float:
    """Logistic of z, written so a far-out value cannot overflow a float.

    The naive 1/(1+exp(-z)) overflows once z drops below about -709, which a
    real cross-section reaches easily: CFO_TO_TOTAL_DEBT was observed at -3180
    against a pool median of 0.30.  Winsorisation is no defence - a 2% trim
    over 25 names rounds down to trimming nothing.  Evaluating the negative
    branch as exp(z)/(1+exp(z)) underflows to 0.0 instead, which puts the
    company at the bottom of the pool, where it belongs.
    """
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _relative_scores(spec: RatioSpec, pool: Mapping[str, float]) -> dict[str, float]:
    """Robust cross-sectional score in [0, 1] for one ratio over one pool.

    Median/MAD rather than mean/std: BIST cross-sections are fat-tailed and a
    winsorised standard deviation is still dragged by whatever survived the
    winsorisation.
    """
    tickers = list(pool)
    raw = _winsorize([_transform(spec, pool[t]) for t in tickers], spec.winsor)
    oriented = [_orient(spec, v) for v in raw]

    centre = _median(oriented)
    mad = _median([abs(v - centre) for v in oriented])

    if mad > 0:
        scale = MAD_SCALE * mad
        return {
            t: _logistic((v - centre) / scale)
            for t, v in zip(tickers, oriented)
        }

    # Degenerate spread (identical values, or a very small pool). Fall back to
    # a rank so the ratio stays usable instead of collapsing to a constant.
    if len(tickers) == 1:
        return {tickers[0]: 0.5}
    order = sorted(range(len(oriented)), key=lambda i: oriented[i])
    ranks = {tickers[idx]: pos / (len(order) - 1) for pos, idx in enumerate(order)}
    # Ties must not be broken by input order.
    by_value: dict[float, list[str]] = {}
    for t, v in zip(tickers, oriented):
        by_value.setdefault(v, []).append(t)
    for tied in by_value.values():
        if len(tied) > 1:
            shared = sum(ranks[t] for t in tied) / len(tied)
            for t in tied:
                ranks[t] = shared
    return ranks


def _blend_anchor(spec: RatioSpec, relative: float, raw_value: float) -> float:
    if spec.anchor is not None:
        absolute: float | None = spec.anchor.score(raw_value)
    elif spec.direction == "BAND":
        absolute = _band_absolute(spec, raw_value)
    else:
        absolute = None
    if absolute is None:
        return relative
    return ANCHOR_BLEND * absolute + (1.0 - ANCHOR_BLEND) * relative


def compute_ratio_weights(
    ratio_set: RatioSet, group: str, composite: str
) -> dict[str, float]:
    """Applicable-ratio weights for one composite of one sector group; sum to 1.

    The share a pillar carries is fixed by config; families split it evenly and
    ratios split their family's share evenly. This is the property that lets the
    ratio set grow without silently reweighting anything.
    """
    pillars = set(ratio_set.pillar_of_composite(composite))
    shares = ratio_set.pillar_shares(group)

    by_pillar: dict[str, dict[str, list[RatioSpec]]] = {}
    for spec in ratio_set.applicable(group):
        if spec.pillar not in pillars:
            continue
        by_pillar.setdefault(spec.pillar, {}).setdefault(spec.family, []).append(spec)

    live = {p: shares.get(p, 0.0) for p in by_pillar if shares.get(p, 0.0) > 0}
    total = sum(live.values())
    if total <= 0:
        return {}

    weights: dict[str, float] = {}
    for pillar, share in live.items():
        families = by_pillar[pillar]
        per_family = (share / total) / len(families)
        for specs in families.values():
            per_ratio = per_family / len(specs)
            for spec in specs:
                weights[spec.name] = per_ratio
    return weights


def score_universe(
    ratio_set: RatioSet,
    observations: Iterable[RatioObservation],
    group_of: Mapping[str, str],
    *,
    min_coverage: float = DEFAULT_MIN_COVERAGE,
    min_pool: int = DEFAULT_MIN_POOL,
) -> dict[str, TickerResult]:
    """Score every ticker present in ``observations`` for one period.

    Each ratio is ranked inside its own sector-group pool; a pool smaller than
    ``min_pool`` falls back to the full universe, because a percentile over
    three companies is not a percentile.
    """
    obs_list = list(observations)
    tickers = sorted({o.ticker for o in obs_list})
    unknown = [t for t in tickers if t not in group_of]
    if unknown:
        raise ScoringError(f"sektor grubu bilinmeyen ticker(lar): {unknown}")

    stray = sorted({o.ratio_name for o in obs_list} - set(ratio_set.specs))
    if stray:
        raise ScoringError(f"rasyo setinde olmayan rasyo(lar): {stray}")

    by_ratio: dict[str, dict[str, RatioObservation]] = {}
    for o in obs_list:
        by_ratio.setdefault(o.ratio_name, {})[o.ticker] = o

    group_members: dict[str, list[str]] = {}
    for t in tickers:
        group_members.setdefault(group_of[t], []).append(t)

    # --- 1) per-ratio cross-sectional scores ------------------------------
    ratio_scores: dict[str, dict[str, float]] = {}
    for ratio_name, per_ticker in by_ratio.items():
        spec = ratio_set.specs[ratio_name]
        if not spec.is_scored:
            continue
        ok_values = {
            t: float(o.value)
            for t, o in per_ticker.items()
            if o.status == STATUS_OK and spec.applicable_to(group_of[t])
        }
        if not ok_values:
            continue
        scores: dict[str, float] = {}
        for grp, members in group_members.items():
            pool = {t: v for t, v in ok_values.items() if t in members}
            if not pool:
                continue
            if len(pool) < min_pool:
                pool = ok_values  # full-universe fallback
            relative = _relative_scores(spec, pool)
            for t in members:
                if t in ok_values:
                    scores[t] = _blend_anchor(spec, relative[t], ok_values[t])
        ratio_scores[ratio_name] = scores

    # --- 2) composites, in two passes so shrinkage has a target -----------
    composites = ratio_set.composites()
    weights = {
        (g, c): compute_ratio_weights(ratio_set, g, c)
        for g in group_members
        for c in composites
    }

    raw: dict[str, dict[str, tuple[float, float, float, int, int]]] = {}
    for t in tickers:
        grp = group_of[t]
        raw[t] = {}
        for comp_name in composites:
            applicable_w = measured_w = good_w = acc = 0.0
            measured = applicable = 0
            for ratio_name, w in weights[(grp, comp_name)].items():
                o = by_ratio.get(ratio_name, {}).get(t)
                if o is not None and o.status == STATUS_NOT_APPLICABLE:
                    continue  # leaves the denominator entirely
                applicable_w += w
                applicable += 1
                if o is None or o.status == STATUS_MISSING:
                    continue
                if o.status in DETERMINATE:
                    s = DETERMINATE[o.status]
                else:
                    s = ratio_scores.get(ratio_name, {}).get(t)
                    if s is None:
                        continue
                measured_w += w
                measured += 1
                acc += w * s
                if s >= GOOD_SCORE_THRESHOLD:
                    good_w += w
            if applicable_w <= 0:
                raw[t][comp_name] = (0.0, 0.0, 0.0, 0, 0)
                continue
            coverage = measured_w / applicable_w
            mean = (acc / measured_w) if measured_w > 0 else 0.0
            raw[t][comp_name] = (
                mean, coverage, good_w / applicable_w, measured, applicable
            )

    pool_median: dict[str, float] = {}
    for comp_name in composites:
        well_covered = [
            raw[t][comp_name][0] for t in tickers if raw[t][comp_name][1] >= min_coverage
        ]
        pool_median[comp_name] = _median(well_covered) if well_covered else 0.5

    results: dict[str, TickerResult] = {}
    for t in tickers:
        comps: dict[str, CompositeResult] = {}
        for comp_name in composites:
            mean, coverage, good_ratio, measured, applicable = raw[t][comp_name]
            if applicable == 0 or coverage < min_coverage:
                comps[comp_name] = CompositeResult(
                    status=RESULT_INSUFFICIENT_COVERAGE, score=None, coverage=coverage,
                    good_ratio=good_ratio, measured=measured, applicable=applicable,
                )
                continue
            # Partial coverage is pulled towards the cross-section rather than
            # being reported as if fully measured.
            shrunk = coverage * mean + (1.0 - coverage) * pool_median[comp_name]
            comps[comp_name] = CompositeResult(
                status=RESULT_OK, score=min(max(shrunk, 0.0), 1.0), coverage=coverage,
                good_ratio=good_ratio, measured=measured, applicable=applicable,
            )
        results[t] = TickerResult(
            ticker=t, group=group_of[t], composites=comps,
            ratio_scores={r: s[t] for r, s in ratio_scores.items() if t in s},
        )
    return results
