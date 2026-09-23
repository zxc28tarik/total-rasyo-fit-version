from __future__ import annotations

"""Rank each engine independently, then show where they agree and fight.

Ranks, not scores (K14, K27).  Two engines weigh different things on different
axes, so 0.80 from one and 0.80 from the other are not the same claim; their
orderings, however, live in the same universe and can be compared.
"""

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from engines.base import STATUS_GATED, STATUS_MISSING, EngineResult


@dataclass(frozen=True)
class BoardRow:
    ticker: str
    ranks: Mapping[str, int | None]
    scores: Mapping[str, float | None]
    raw: Mapping[str, float | None] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    @property
    def opinions(self) -> int:
        """How many engines actually reached a verdict on this name."""
        return sum(1 for r in self.ranks.values() if r is not None)

    @property
    def spread(self) -> int | None:
        """Widest disagreement in rank, or None with fewer than two opinions."""
        got = [r for r in self.ranks.values() if r is not None]
        return max(got) - min(got) if len(got) >= 2 else None


def rank_engine(results: Mapping[str, EngineResult]) -> dict[str, int | None]:
    """Rank one engine's output.  Rank 1 is best.

    K26: a MISSING result is unranked, because a company nobody could measure
    is not the worst company - that conflation is the v1 defect this project
    exists to remove.  A GATED result *is* ranked, at the bottom, because a
    veto is a measured verdict.
    """
    ranked = [(t, r) for t, r in results.items() if r.status != STATUS_MISSING]
    # Sort: clean before gated, then by score descending, then ticker so ties
    # never depend on dict order.
    ranked.sort(key=lambda kv: (kv[1].status == STATUS_GATED,
                                -float(kv[1].score), kv[0]))

    out: dict[str, int | None] = {t: None for t in results}
    for position, (ticker, _) in enumerate(ranked, start=1):
        out[ticker] = position
    return out


def build_board(
    engine_results: Mapping[str, Mapping[str, EngineResult]],
    raw: Mapping[str, Mapping[str, float | None]] | None = None,
) -> list[BoardRow]:
    """One row per ticker, every engine's rank and score side by side."""
    ranks_by_engine = {e: rank_engine(res) for e, res in engine_results.items()}
    tickers = sorted({t for res in engine_results.values() for t in res})

    rows: list[BoardRow] = []
    for ticker in tickers:
        ranks, scores, notes = {}, {}, []
        for engine, res in engine_results.items():
            r = res.get(ticker)
            ranks[engine] = ranks_by_engine[engine].get(ticker)
            scores[engine] = None if r is None else r.score
            if r is not None:
                notes.extend(r.notes)
        rows.append(BoardRow(
            ticker=ticker, ranks=ranks, scores=scores,
            raw=dict((raw or {}).get(ticker, {})),
            notes=tuple(dict.fromkeys(notes)),
        ))

    # Best average rank first; names nobody ranked sink to the bottom.
    def key(row: BoardRow):
        got = [r for r in row.ranks.values() if r is not None]
        return (0 if got else 1, sum(got) / len(got) if got else 0, row.ticker)

    rows.sort(key=key)
    return rows


def consensus(rows: Sequence[BoardRow], top_n: int) -> list[tuple[str, float]]:
    """Names every engine that had an opinion put in its top `top_n`.

    K28: agreement needs at least two opinions.  One engine liking a stock is
    not consensus, however much it likes it.
    """
    out = []
    for row in rows:
        got = [r for r in row.ranks.values() if r is not None]
        if len(got) < 2:
            continue
        if all(r <= top_n for r in got):
            out.append((row.ticker, sum(got) / len(got)))
    out.sort(key=lambda kv: (kv[1], kv[0]))
    return out


def divergence(rows: Sequence[BoardRow]) -> list[tuple[str, int]]:
    """Names the engines disagree about, widest rank gap first.

    This is the research queue: not an error to be averaged away, but the one
    place the board actively points at.
    """
    out = [(row.ticker, row.spread) for row in rows if row.spread is not None]
    out = [(t, s) for t, s in out if s > 0]
    out.sort(key=lambda kv: (-kv[1], kv[0]))
    return out
