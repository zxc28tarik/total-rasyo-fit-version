from __future__ import annotations

"""Render the board: a terminal table and the same rows as CSV.

Deliberately plain text and pure stdlib.  The board's value is in what it
shows, not in how it is drawn, and a dependency here would spread upward.
"""

from typing import Sequence

from board.comparison import BoardRow, consensus, divergence

UNRANKED = "-"


def _fmt(value, places=3):
    return UNRANKED if value is None else f"{value:.{places}f}"


def render_table(rows: Sequence[BoardRow], raw_columns: Sequence[str] = ()) -> str:
    if not rows:
        return "(bos tahta)\n"

    engines = list(rows[0].ranks)
    head = ["HISSE"] + [f"{e}#" for e in engines] + [f"{e}~" for e in engines]
    head += list(raw_columns)

    body = []
    for row in rows:
        line = [row.ticker]
        line += [UNRANKED if row.ranks[e] is None else str(row.ranks[e])
                 for e in engines]
        line += [_fmt(row.scores[e]) for e in engines]
        line += [_fmt(row.raw.get(c), 2) for c in raw_columns]
        body.append(line)

    widths = [max(len(str(r[i])) for r in [head] + body) for i in range(len(head))]
    out = ["  ".join(str(c).ljust(widths[i]) for i, c in enumerate(head)),
           "  ".join("-" * w for w in widths)]
    out += ["  ".join(str(c).ljust(widths[i]) for i, c in enumerate(line))
            for line in body]

    caveats = sorted({n for row in rows for n in row.notes})
    if caveats:
        out.append("")
        out.append("UYARILAR")
        out += [f"  * {c}" for c in caveats]
    return "\n".join(out) + "\n"


def render_lists(rows: Sequence[BoardRow], top_n: int = 10) -> str:
    """The two lists the board exists for."""
    out = [f"UZLASMA (her motorun ilk {top_n}'i)"]
    agreed = consensus(rows, top_n=top_n)
    out += [f"  {t:8} ortalama sira {r:.1f}" for t, r in agreed] or ["  (yok)"]

    out += ["", "AYRISMA (motorlar catisiyor -> arastirma kuyrugu)"]
    split = divergence(rows)[:top_n]
    out += [f"  {t:8} sira farki {s}" for t, s in split] or ["  (yok)"]
    return "\n".join(out) + "\n"


def render_csv(rows: Sequence[BoardRow], raw_columns: Sequence[str] = ()) -> str:
    if not rows:
        return ""
    engines = list(rows[0].ranks)
    head = ["ticker"] + [f"{e}_rank" for e in engines]
    head += [f"{e}_score" for e in engines] + list(raw_columns)
    lines = [",".join(head)]
    for row in rows:
        cells = [row.ticker]
        cells += ["" if row.ranks[e] is None else str(row.ranks[e]) for e in engines]
        cells += ["" if row.scores[e] is None else f"{row.scores[e]:.6f}"
                  for e in engines]
        cells += ["" if row.raw.get(c) is None else f"{row.raw[c]:.6f}"
                  for c in raw_columns]
        lines.append(",".join(cells))
    return "\n".join(lines) + "\n"
