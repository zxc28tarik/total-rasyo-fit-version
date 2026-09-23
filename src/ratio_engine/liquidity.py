from __future__ import annotations

"""Traded liquidity: average daily turnover in TRY.

K13 keeps this strictly apart from balance-sheet liquidity.  The current and
quick ratios stay in the LIQ pillar on the quality axis; this number is a hard
gate, because a signal on a stock that trades 200k TRY a day is real and
unusable at the same time.

Only the arithmetic lives here.  Ingesting volume is the upstream project's
job, and pulling it in would cost this package its zero-dependency property
(K10).  The caller hands over rows; this module never fetches anything.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping

from ratio_engine.evaluator import _is_finite

STATUS_OK = "OK"
STATUS_MISSING = "MISSING"

DEFAULT_WINDOW_DAYS = 60
DEFAULT_MIN_DAYS = 40


@dataclass(frozen=True)
class LiquidityResult:
    value: float | None
    status: str
    days_used: int


def adv_try(
    bars: Iterable[Mapping[str, Any]],
    as_of: date,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    min_days: int = DEFAULT_MIN_DAYS,
) -> LiquidityResult:
    """Mean of close x volume over the trailing `window_days` trading bars.

    Trading bars, not calendar days: the window is the last N rows at or
    before ``as_of``, so holidays and halts shorten the calendar span rather
    than diluting the average with days the stock could not trade.

    ``days_used`` is reported even when the status is MISSING, because "how
    short was it" is what a coverage report needs and MISSING alone does not
    say.
    """
    usable: list[tuple[date, float]] = []
    for bar in bars:
        td = bar.get("trade_date")
        if not isinstance(td, date) or td > as_of:
            continue
        close, volume = bar.get("close"), bar.get("volume")
        if not (_is_finite(close) and _is_finite(volume)):
            continue
        usable.append((td, float(close) * float(volume)))

    usable.sort()
    window = usable[-window_days:]
    days_used = len(window)

    if days_used < min_days:
        return LiquidityResult(None, STATUS_MISSING, days_used)

    value = sum(v for _, v in window) / days_used
    if not _is_finite(value):
        return LiquidityResult(None, STATUS_MISSING, days_used)
    return LiquidityResult(value, STATUS_OK, days_used)
