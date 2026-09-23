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
