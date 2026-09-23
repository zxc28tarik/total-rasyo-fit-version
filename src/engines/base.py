from __future__ import annotations

"""What every engine returns, and the vocabulary they share.

An engine turns the composites of ``ratio_engine.scoring`` into one number per
ticker.  Engines differ in which axes they weigh and which gates they apply;
they do not differ in what they hand back, because the board ranks them side
by side and a ranking across inconsistent shapes means nothing.

Three statuses, mirroring the ratio layer's split between unmeasured and
measured-and-bad::

    OK       scored.
    MISSING  not enough measured input to score at all.
    GATED    scored, and a gate vetoed it.  The score stays visible so the
             board can show what was vetoed instead of hiding the company.
"""

from dataclasses import dataclass
from typing import Mapping, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from ratio_engine.scoring import TickerResult

STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_GATED = "GATED"

_STATUSES = (STATUS_OK, STATUS_MISSING, STATUS_GATED)

# Below this a multiplied score is a veto rather than a small number.
GATED_BELOW = 1e-9


class EngineError(ValueError):
    pass


@dataclass(frozen=True)
class EngineResult:
    engine: str
    ticker: str
    score: float | None
    status: str
    axes: Mapping[str, float]
    gates: Mapping[str, float]
    coverage: float
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise EngineError(f"{self.ticker}: bilinmeyen status {self.status!r}")
        if self.status == STATUS_MISSING:
            if self.score is not None:
                raise EngineError(
                    f"{self.ticker}: status MISSING ise score None olmali"
                )
        elif self.score is None:
            raise EngineError(
                f"{self.ticker}: status {self.status} ise score sonlu olmali"
            )
        if not 0.0 <= float(self.coverage) <= 1.0:
            raise EngineError(f"{self.ticker}: coverage 0..1 disinda")


class Engine(Protocol):
    name: str

    def run(self, universe: Mapping[str, "TickerResult"]) -> dict[str, EngineResult]:
        ...


def apply_gates(
    score: float, gates: Mapping[str, float]
) -> tuple[float, dict[str, float], str]:
    """Multiply the axis score by every gate (K15).

    Gates multiply because a company that is cheap and about to default must
    not be compensated for the second by the first.  Addition allows exactly
    that, and it is how value traps reach the top of a list.
    """
    applied = {name: float(g) for name, g in gates.items()}
    out = float(score)
    for g in applied.values():
        out *= g
    status = STATUS_GATED if applied and out <= GATED_BELOW else STATUS_OK
    return out, applied, status


def weigh_axes(axes: Mapping[str, float], weights: Mapping[str, float]) -> float:
    """Weighted sum of axis scores, over exactly the declared axes.

    No renormalising over whatever happens to be present: an engine whose axis
    is unavailable must say so (K24), not quietly redistribute that axis's
    weight.  Otherwise two companies carry differently defined scores into the
    same ranking, and the ranking is what the decision rests on (K14).
    """
    mismatch = set(weights) ^ set(axes)
    if mismatch:
        raise EngineError(f"eksen/agirlik uyusmuyor: {sorted(mismatch)}")
    return sum(axes[k] * weights[k] for k in weights)
