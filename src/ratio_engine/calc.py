from __future__ import annotations

"""v2 ratio computation: three outcomes where v1 had one.

v1 collapsed every failure into a single ``is_na`` boolean
(``ratios_calc.compute_ratios_for_ticker``).  That conflated three unrelated
situations, and the consequence was measured on the live code: a debt-free
company has no interest expense, so ``INTEREST_COVERAGE`` went NA, the NaN
propagated through ``rsc_scoring._wmean`` and wiped ``rsc_core_norm`` entirely,
and ``run_daily_pipeline`` then filled the resulting NaN M1 with 0.0.  The
company was scored zero on quality for the crime of having no debt.

v2 separates them::

    NOT_APPLICABLE  the ratio is meaningless here (a service business has no
                    inventory, so DIO is not a bad score - it is no score).
                    Leaves the denominator entirely.
    MISSING         a required field is null, or a cross-quarter aggregate
                    could not be formed. Stays in the denominator and lowers
                    coverage, because this is genuinely unmeasured.
    BEST / WORST    mathematically undefined but economically unambiguous.
                    Counts as measured and carries a score.
    OK              computed.

The AST evaluator, ``QuarterSeries`` and the field-derivation helper come from
``ratio_engine.evaluator``, vendored unchanged out of the upstream project; only
the outcome contract here is new.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

from ratio_engine.spec import RatioSet, RatioSpec
from ratio_engine.evaluator import (
    QuarterSeries,
    derive_fields_per_ticker,
    safe_eval_condition,
    safe_eval_expr,
    _is_finite,
)


STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_BEST = "BEST"
STATUS_WORST = "WORST"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"


class RatioCalcV2Error(ValueError):
    pass


@dataclass(frozen=True)
class RatioOutcome:
    ticker: str
    period_end: date
    version_tag: str
    ratio_name: str
    value: float | None
    status: str

    def __post_init__(self) -> None:
        if self.status == STATUS_OK and not _is_finite(self.value):
            raise RatioCalcV2Error(
                f"{self.ticker}/{self.ratio_name}: status OK ise deger sonlu olmali"
            )
        if self.status != STATUS_OK and self.value is not None:
            raise RatioCalcV2Error(
                f"{self.ticker}/{self.ratio_name}: status {self.status} ise deger None olmali"
            )


def _requires_present(spec: RatioSpec, env: Mapping[str, Any]) -> bool:
    """True when every declared field is present on the current period row.

    This is the fast path for a field that is simply not ingested yet.  A field
    that exists now but is absent in an earlier quarter is caught later, when
    the cross-quarter aggregate returns None.
    """
    for field in spec.requires:
        if field not in env or env[field] is None:
            return False
    return True


def _domain_holds(spec: RatioSpec, env: Mapping[str, Any], qs: QuarterSeries, pe: date) -> bool | None:
    """True/False for the domain guard, or None when it cannot be evaluated.

    A guard that raises means we cannot tell whether the ratio is in domain, so
    the outcome is MISSING rather than an assumed best or worst case.
    """
    for rule in spec.domain:
        try:
            if not safe_eval_condition(rule, dict(env), qs, pe):
                return False
        except Exception:
            return None
    return True


def _evaluate(spec: RatioSpec, env: Mapping[str, Any], qs: QuarterSeries, pe: date) -> float | None:
    try:
        value = safe_eval_expr(spec.formula, dict(env), qs, pe)
    except Exception:
        return None
    return float(value) if _is_finite(value) else None


def resolve_ratio(
    spec: RatioSpec,
    env: Mapping[str, Any],
    qs: QuarterSeries,
    pe: date,
    group: str,
) -> tuple[float | None, str]:
    """Resolve one ratio for one period into (value, status).

    Order matters: applicability first (a ratio that does not apply is never
    "missing"), then required fields, then the domain guard, then the formula.
    """
    if spec.is_scored and not spec.applicable_to(group):
        return None, STATUS_NOT_APPLICABLE

    if not _requires_present(spec, env):
        return None, STATUS_MISSING

    holds = _domain_holds(spec, env, qs, pe)
    if holds is None:
        return None, STATUS_MISSING
    if not holds:
        if spec.out_of_domain == STATUS_NOT_APPLICABLE:
            return None, STATUS_NOT_APPLICABLE
        if spec.out_of_domain == STATUS_BEST:
            return None, STATUS_BEST
        if spec.out_of_domain == STATUS_WORST:
            return None, STATUS_WORST
        return None, STATUS_MISSING

    value = _evaluate(spec, env, qs, pe)
    if value is None:
        return None, STATUS_MISSING
    return value, STATUS_OK


def compute_ratios_for_ticker(
    ticker: str,
    rows: Sequence[Mapping[str, Any]],
    ratio_set: RatioSet,
    group: str,
    price_map: Mapping[tuple[str, date], float] | None = None,
) -> list[RatioOutcome]:
    """Compute every scored ratio for one ticker across its quarters.

    Intermediates are evaluated in declaration order and injected into the
    environment so later ratios can read them by name, but they never produce
    an outcome row: they are plumbing, not measurements.  v1 had no such role
    and faked it by making ``EV_PROXY`` a VAL ratio that a later filter had to
    exclude by hand.
    """
    if group not in ratio_set.sector_groups:
        raise RatioCalcV2Error(f"bilinmeyen sektor grubu: {group!r}")

    prepared = [dict(r) for r in rows]
    for rec in prepared:
        for key, value in list(rec.items()):
            if value is not None and not isinstance(value, (str, date)):
                try:
                    if value != value:  # NaN
                        rec[key] = None
                except Exception:
                    pass
    prepared = derive_fields_per_ticker(prepared)
    qs = QuarterSeries(prepared)
    prices = price_map or {}

    out: list[RatioOutcome] = []
    for rec in prepared:
        pe = rec["period_end"]
        version_tag = str(rec.get("version_tag", "ORIGINAL"))
        t0 = rec.get("t0_date")
        env: dict[str, Any] = dict(rec)
        env["price"] = prices.get((ticker, t0)) if t0 is not None else None

        for name in ratio_set.order:
            spec = ratio_set.specs[name]
            value, status = resolve_ratio(spec, env, qs, pe, group)
            # Intermediates feed the environment; a failed one leaves None
            # behind so dependants resolve to MISSING rather than inventing a
            # substitute value.
            env[name] = value
            if spec.is_scored:
                out.append(
                    RatioOutcome(
                        ticker=ticker,
                        period_end=pe,
                        version_tag=version_tag,
                        ratio_name=name,
                        value=value,
                        status=status,
                    )
                )
    return out


def status_summary(outcomes: Iterable[RatioOutcome]) -> dict[str, int]:
    counts: dict[str, int] = {
        STATUS_OK: 0, STATUS_MISSING: 0, STATUS_BEST: 0,
        STATUS_WORST: 0, STATUS_NOT_APPLICABLE: 0,
    }
    for o in outcomes:
        counts[o.status] += 1
    return counts
