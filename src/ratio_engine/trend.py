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
from typing import Sequence

from ratio_engine.evaluator import _is_finite

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
