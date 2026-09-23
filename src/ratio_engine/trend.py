from __future__ import annotations

"""(level, slope, stability) over a trailing window of quarters.

K8 settled that stability is not a ratio: it is the third component of a
triple the scoring layer derives across quarters.  This module derives all
three and reports them in raw units, because the cross-sectional machinery in
``ratio_engine.scoring`` already winsorises and rescales by median/MAD.  A
second normalisation here would only add a constant nobody has measured.

The five-outcome contract of ``calc`` applies unchanged: too few quarters
means ``MISSING``, never a silent 0.0.
"""

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence, TYPE_CHECKING

from ratio_engine.evaluator import _is_finite, _quarter_end

if TYPE_CHECKING:
    from ratio_engine.calc import RatioOutcome

STATUS_OK = "OK"
STATUS_MISSING = "MISSING"

DEFAULT_WINDOW = 8
DEFAULT_MIN_QUARTERS = 6


class TrendError(ValueError):
    pass


@dataclass(frozen=True)
class TrendTriple:
    ratio_name: str
    level: float | None
    slope: float | None
    stability: float | None
    status: str
    quarters_used: int

    def __post_init__(self) -> None:
        components = (self.level, self.slope, self.stability)
        if self.status == STATUS_OK:
            if not all(_is_finite(c) for c in components):
                raise TrendError(
                    f"{self.ratio_name}: status OK ise uc bilesen de sonlu olmali"
                )
        elif any(c is not None for c in components):
            raise TrendError(
                f"{self.ratio_name}: status {self.status} ise bilesenler None olmali"
            )


def _ols_slope(points: Sequence[tuple[int, float]]) -> float | None:
    """Least-squares gradient of value against quarter index.

    The x axis is the absolute quarter index, not the position in the list, so
    a missing quarter leaves a real gap (K20) and does not tilt the fit.
    """
    n = len(points)
    if n < 2:
        return None
    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n
    sxx = sum((p[0] - mean_x) ** 2 for p in points)
    if sxx <= 0.0:
        return None
    sxy = sum((p[0] - mean_x) * (p[1] - mean_y) for p in points)
    slope = sxy / sxx
    return slope if _is_finite(slope) else None


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _residual_mad(points: Sequence[tuple[int, float]], slope: float) -> float:
    """Median absolute deviation of the residuals around the fitted line.

    Median/MAD rather than RMSE, for the same reason scoring uses them (K7):
    one restated quarter should not decide whether a company looks stable.
    Returned in raw ratio units and oriented LOWER_BETTER by the caller (K19).

    Deliberately not imported from ``scoring``: that would point this module
    at the layer above it.  The duplication is three lines and the coupling
    would be permanent.
    """
    n = len(points)
    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n
    intercept = mean_y - slope * mean_x
    residuals = [p[1] - (slope * p[0] + intercept) for p in points]
    centre = _median(residuals)
    return _median([abs(r - centre) for r in residuals])


def _quarter_index(value: date) -> int:
    anchor = _quarter_end(value)
    return anchor.year * 4 + ((anchor.month - 1) // 3)


def compute_trend(
    outcomes: Iterable["RatioOutcome"],
    ratio_name: str,
    period_end: date,
    *,
    window: int = DEFAULT_WINDOW,
    min_quarters: int = DEFAULT_MIN_QUARTERS,
) -> TrendTriple:
    """Derive (level, slope, stability) for one ratio of one ticker.

    ``level`` is the value at ``period_end`` itself, not the window mean: the
    triple says "where it is, where it is heading, how steadily", and the
    first of those is a point reading.
    """
    end_index = _quarter_index(period_end)
    first_index = end_index - (window - 1)

    points: list[tuple[int, float]] = []
    for o in outcomes:
        if o.ratio_name != ratio_name or o.status != STATUS_OK:
            continue
        if not _is_finite(o.value):
            continue
        idx = _quarter_index(o.period_end)
        if first_index <= idx <= end_index:
            points.append((idx, float(o.value)))

    points.sort()
    used = len(points)

    if used < min_quarters:
        return TrendTriple(ratio_name, None, None, None, STATUS_MISSING, used)

    level = next((v for idx, v in reversed(points) if idx == end_index), None)
    if level is None:
        return TrendTriple(ratio_name, None, None, None, STATUS_MISSING, used)

    slope = _ols_slope(points)
    if slope is None:
        return TrendTriple(ratio_name, None, None, None, STATUS_MISSING, used)

    stability = _residual_mad(points, slope)
    if not _is_finite(stability):
        return TrendTriple(ratio_name, None, None, None, STATUS_MISSING, used)

    return TrendTriple(ratio_name, level, slope, stability, STATUS_OK, used)
