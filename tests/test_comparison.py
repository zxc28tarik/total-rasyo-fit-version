"""The board: one row per stock, engines side by side.

The point of the screen is not a better single number.  It is that where
independent engines agree you have some confidence, and where they fight you
have a research queue - and averaging them away destroys exactly that.
"""
from __future__ import annotations

import pytest

from board.comparison import build_board, consensus, divergence, rank_engine
from engines.base import EngineResult


def _r(ticker, score, status="OK", engine="e"):
    return EngineResult(engine, ticker, score, status,
                        {"a": score if score is not None else 0.0}, {},
                        0.8, ())


def test_rank_one_is_the_best_score():
    ranks = rank_engine({"A": _r("A", 0.9), "B": _r("B", 0.5), "C": _r("C", 0.7)})
    assert ranks["A"] == 1
    assert ranks["C"] == 2
    assert ranks["B"] == 3


def test_missing_results_are_unranked_not_ranked_last():
    """A company nobody could measure is not the worst company.  Conflating
    those two is the v1 defect this project exists to remove."""
    ranks = rank_engine({"A": _r("A", 0.9),
                         "GHOST": _r("GHOST", None, "MISSING"),
                         "B": _r("B", 0.5)})
    assert ranks["GHOST"] is None
    assert ranks["A"] == 1
    assert ranks["B"] == 2


def test_gated_results_are_ranked_last_among_the_scored():
    """A measured veto IS a verdict, so it ranks - at the bottom."""
    ranks = rank_engine({"A": _r("A", 0.9),
                         "VETOED": _r("VETOED", 0.0, "GATED"),
                         "B": _r("B", 0.5)})
    assert ranks["VETOED"] == 3
    assert ranks["B"] == 2


def test_a_gated_company_ranks_below_a_low_but_clean_one():
    ranks = rank_engine({"LOW": _r("LOW", 0.01),
                         "VETOED": _r("VETOED", 0.0, "GATED")})
    assert ranks["LOW"] < ranks["VETOED"]


def test_ties_break_deterministically_by_ticker():
    first = rank_engine({"B": _r("B", 0.5), "A": _r("A", 0.5)})
    second = rank_engine({"A": _r("A", 0.5), "B": _r("B", 0.5)})
    assert first == second
    assert first["A"] == 1


def test_board_puts_every_engine_on_one_row_per_stock():
    board = build_board({
        "one": {"A": _r("A", 0.9, engine="one"), "B": _r("B", 0.2, engine="one")},
        "two": {"A": _r("A", 0.1, engine="two"), "B": _r("B", 0.8, engine="two")},
    })
    rows = {r.ticker: r for r in board}
    assert rows["A"].ranks == {"one": 1, "two": 2}
    assert rows["B"].ranks == {"one": 2, "two": 1}


def test_consensus_lists_names_every_engine_ranks_highly():
    board = build_board({
        "one": {"GOOD": _r("GOOD", 0.9, engine="one"),
                "MEH": _r("MEH", 0.5, engine="one"),
                "BAD": _r("BAD", 0.1, engine="one")},
        "two": {"GOOD": _r("GOOD", 0.8, engine="two"),
                "MEH": _r("MEH", 0.4, engine="two"),
                "BAD": _r("BAD", 0.2, engine="two")},
    })
    assert [t for t, _ in consensus(board, top_n=1)] == ["GOOD"]


def test_divergence_lists_names_the_engines_disagree_about():
    board = build_board({
        "one": {"SPLIT": _r("SPLIT", 0.9, engine="one"),
                "X": _r("X", 0.5, engine="one"),
                "Y": _r("Y", 0.1, engine="one")},
        "two": {"SPLIT": _r("SPLIT", 0.1, engine="two"),
                "X": _r("X", 0.5, engine="two"),
                "Y": _r("Y", 0.9, engine="two")},
    })
    worst = divergence(board)[0]
    assert worst[0] in ("SPLIT", "Y")
    assert worst[1] == 2


def test_a_name_only_one_engine_could_score_is_in_neither_list():
    """K28.  One opinion is not agreement, and it cannot be a disagreement."""
    board = build_board({
        "one": {"LONE": _r("LONE", 0.99, engine="one"),
                "P": _r("P", 0.5, engine="one"), "Q": _r("Q", 0.4, engine="one")},
        "two": {"LONE": _r("LONE", None, "MISSING", engine="two"),
                "P": _r("P", 0.5, engine="two"), "Q": _r("Q", 0.4, engine="two")},
    })
    assert "LONE" not in [t for t, _ in consensus(board, top_n=1)]
    assert "LONE" not in [t for t, _ in divergence(board)]


def test_divergence_is_measured_on_rank_not_score():
    """K27.  Two engines' scores are differently defined; 0.80 and 0.80 do not
    mean the same thing.  Ranks live in the same universe."""
    board = build_board({
        "one": {"A": _r("A", 0.90, engine="one"), "B": _r("B", 0.89, engine="one")},
        "two": {"A": _r("A", 0.10, engine="two"), "B": _r("B", 0.11, engine="two")},
    })
    # Scores barely differ; ranks are fully inverted, and that is the signal.
    assert divergence(board)[0][1] == 1


def test_board_is_ordered_and_stable():
    board = build_board({
        "one": {"B": _r("B", 0.5, engine="one"), "A": _r("A", 0.9, engine="one")},
    })
    assert [r.ticker for r in board] == ["A", "B"]


# --- report ---------------------------------------------------------------

def test_report_row_carries_ranks_and_raw_ratios_side_by_side():
    from board.report import render_table

    board = build_board(
        {"one": {"A": _r("A", 0.9, engine="one")}},
        raw={"A": {"PE_TTM": 8.4, "PB": 1.2}},
    )
    text = render_table(board, raw_columns=["PE_TTM", "PB"])
    assert "A" in text
    assert "8.4" in text
    assert "PE_TTM" in text


def test_unapplied_gates_are_visible_in_the_output():
    """K22: the screen must be able to say it scored without a risk check."""
    from board.report import render_table

    gated = EngineResult("one", "A", 0.5, "OK", {"a": 0.5}, {"G_risk": 1.0},
                         0.8, ("G_risk uygulanmadi: FX_DEBT_RATIO olculemedi",))
    text = render_table(build_board({"one": {"A": gated}}))
    assert "G_risk uygulanmadi" in text


def test_csv_and_table_carry_the_same_rows():
    from board.report import render_csv, render_table

    board = build_board({
        "one": {"A": _r("A", 0.9, engine="one"), "B": _r("B", 0.2, engine="one")},
    })
    csv_lines = render_csv(board).strip().splitlines()
    assert len(csv_lines) == 3  # header + two names
    text = render_table(board)
    for ticker in ("A", "B"):
        assert ticker in text
        assert any(line.startswith(ticker + ",") for line in csv_lines[1:])


def test_an_unranked_name_renders_without_inventing_a_rank():
    from board.report import render_table

    board = build_board({"one": {"GHOST": _r("GHOST", None, "MISSING", engine="one")}})
    text = render_table(board)
    assert "GHOST" in text
    assert "-" in text


# --- end to end -----------------------------------------------------------

def test_the_whole_chain_produces_a_board():
    """spec -> calc -> scoring -> two engines -> board -> rendered table.

    The unit tests pin each contract; only this one proves they fit together.
    """
    from datetime import date

    from board.report import render_lists
    from engines.kalite_bilesik import KaliteBilesik
    from engines.saf_deger import SafDeger
    from ratio_engine.calc import compute_ratios_for_ticker
    from ratio_engine.scoring import RatioObservation, score_universe
    from tests._fixtures import real_set
    from tests.test_calc import QUARTERS, _rows

    rs = real_set()
    obs, group_of = [], {}
    for i, ticker in enumerate(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]):
        rows = _rows(net_income=100.0 + 40 * i, total_equity=4000.0 - 200 * i,
                     revenue=1000.0 + 100 * i)
        outs = compute_ratios_for_ticker(
            ticker, rows, rs, "NONFIN", {(ticker, pe): 20.0 + i for pe in QUARTERS}
        )
        for o in outs:
            if o.period_end == QUARTERS[-1]:
                obs.append(RatioObservation(ticker, o.ratio_name, o.value, o.status))
        group_of[ticker] = "NONFIN"

    universe = score_universe(rs, obs, group_of)
    stability = {t: (i + 1) / 6 for i, t in enumerate(sorted(universe))}

    board = build_board({
        "saf_deger": SafDeger().run(universe),
        "kalite": KaliteBilesik(stability=stability).run(universe),
    })

    assert len(board) == 6
    assert all(set(row.ranks) == {"saf_deger", "kalite"} for row in board)

    from board.report import render_table
    text = render_table(board)
    assert "saf_deger#" in text
    for ticker in group_of:
        assert ticker in text

    lists = render_lists(board, top_n=3)
    assert "UZLASMA" in lists and "AYRISMA" in lists
