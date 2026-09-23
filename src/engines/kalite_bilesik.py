from __future__ import annotations

"""Kalite Bilesik: quality, plus how steadily it was earned.

K8 settled that stability is not a ratio but the third component of the
(level, slope, stability) triple the layer above derives.  This is that
component's first consumer: a 0.60 margin held for eight quarters is not the
same business as a 0.60 averaged out of a 0.2 and a 1.0, and the quality
composite alone cannot tell them apart.

Stability readings are supplied by the caller, already scored into 0..1 by the
cross-sectional machinery, because turning a raw residual MAD into a
comparable number is the scoring layer's job and not this engine's (K19).
"""

from typing import Mapping

from engines.base import (
    STATUS_MISSING, EngineError, EngineResult, apply_gates, weigh_axes,
)

NAME = "kalite_bilesik"
WEIGHTS = {"quality": 0.70, "stability": 0.30}

ACCRUALS_VETO_BELOW = 0.20


class KaliteBilesik:
    name = NAME

    def __init__(self, stability: Mapping[str, float]):
        self.stability = stability

    def run(self, universe: Mapping[str, object]) -> dict[str, EngineResult]:
        out: dict[str, EngineResult] = {}
        for ticker, res in universe.items():
            comp = res.composites.get("quality")
            stab = self.stability.get(ticker)

            missing = []
            if comp is None or comp.score is None:
                missing.append("quality kompoziti skorlanamadi")
            if stab is None:
                missing.append("istikrar ekseni olculemedi")
            if missing:
                # K24: the lost axis's weight is not handed to the survivor.
                out[ticker] = EngineResult(
                    NAME, ticker, None, STATUS_MISSING, {}, {},
                    float(comp.coverage) if comp else 0.0, tuple(missing),
                )
                continue

            axes = {"quality": float(comp.score), "stability": float(stab)}
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
