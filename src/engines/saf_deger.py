from __future__ import annotations

"""Saf Deger: one axis, one gate.

The thesis is that cheapness only counts where the accounting can be believed.
A company trading at a low multiple because its earnings are an accrual
artefact is not cheap, it is mismeasured - and that is how value traps get to
the top of a screen.  So the value composite carries the whole score and the
accruals gate can take it all away (K15).
"""

from typing import Mapping

from engines.base import (
    STATUS_MISSING, EngineResult, apply_gates, weigh_axes,
)

NAME = "saf_deger"
WEIGHTS = {"value": 1.0}

# K23: below this the accruals reading is a veto, not a deduction.  A hard
# threshold rather than a smooth multiplier, because a smooth one would make
# the gate a second axis and double-count what the composite already holds.
# Unvalidated - it sits with the constants in DEVIR.md section 7.
ACCRUALS_VETO_BELOW = 0.20


class SafDeger:
    name = NAME

    def run(self, universe: Mapping[str, object]) -> dict[str, EngineResult]:
        out: dict[str, EngineResult] = {}
        for ticker, res in universe.items():
            comp = res.composites.get("value")
            if comp is None or comp.score is None:
                out[ticker] = EngineResult(
                    NAME, ticker, None, STATUS_MISSING, {}, {},
                    comp.coverage if comp else 0.0,
                    ("value kompoziti skorlanamadi",),
                )
                continue

            axes = {"value": float(comp.score)}
            notes: list[str] = []

            accruals = res.ratio_scores.get("ACCRUALS_TO_ASSETS")
            if accruals is None:
                gate = 1.0
                notes.append(
                    "G_muhasebe uygulanmadi: ACCRUALS_TO_ASSETS olculemedi"
                )
            else:
                gate = 0.0 if accruals < ACCRUALS_VETO_BELOW else 1.0

            score, applied, status = apply_gates(
                weigh_axes(axes, WEIGHTS), {"G_muhasebe": gate}
            )
            out[ticker] = EngineResult(
                NAME, ticker, score, status, axes, applied,
                float(comp.coverage), tuple(notes),
            )
        return out
