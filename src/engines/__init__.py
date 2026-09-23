"""Engines: independent opinions over the same scored universe.

Each engine reads ``ratio_engine.scoring`` output and returns one
``EngineResult`` per ticker.  The point is not a better single number - it is
several honest numbers whose agreement and disagreement the board can show.
"""
from engines.base import (
    Engine, EngineError, EngineResult, apply_gates, weigh_axes,
)

__all__ = ["Engine", "EngineError", "EngineResult", "apply_gates", "weigh_axes"]
