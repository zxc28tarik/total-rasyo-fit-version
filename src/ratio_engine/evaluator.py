from __future__ import annotations

"""Safe formula evaluator, vendored from the Total Rasyo project.

Copied verbatim from ``src/analytics/ratios_calc.py`` at commit adf3f81 of
zxc28tarik/TOTAL-RASYO-HESAPLAYICI.  Only the DB and pandas layers were left
behind: ``fill_missing_t0_dates``, ``fetch_financials`` and ``apply_unit_scale``
read from PostgreSQL and are not needed to evaluate a ratio formula.

What remains is pure standard library, which is what lets this package run with
no third-party dependency at all.  If the upstream evaluator changes, this file
does not follow automatically - that is the accepted cost of the split.

The formula language:
  fields          bare identifiers, resolved from the period row
  avg(x)          mean of this quarter and the previous one
  lag(x, n)       value n quarters back          lag4q(x) == lag(x, 4)
  sum4q(x)        trailing four-quarter sum      ttm(x) is an alias
  days_in_period()  calendar length of the quarter, 91 when unknown
  abs, min, max, log, log1p, coalesce, nz
Anything else is rejected at parse time.
"""

import ast
import math
from datetime import date, datetime, timedelta
from typing import List

OPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b, ast.USub: lambda a: -a}


CMP = {ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b, ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Is: lambda a, b: a is b, ast.IsNot: lambda a, b: a is not b}


ALLOWED_FUNCS = {"avg", "lag", "lag4q", "sum4q", "ttm", "abs", "coalesce", "nz", "days_in_period", "log", "log1p", "max", "min"}


def coalesce(*args):
    for a in args:
        if a is not None:
            return a
    return None


def nz(x, default=0):
    return default if x is None else x


def _is_finite(x):
    try:
        return x is not None and math.isfinite(float(x))
    except Exception:
        return False


def _quarter_end(value: date) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValueError("period_end date olmali")
    quarter = (value.month - 1) // 3
    next_month = quarter * 3 + 4
    year = value.year
    if next_month > 12:
        next_month -= 12
        year += 1
    return date(year, next_month, 1) - timedelta(days=1)


def _shift_quarter_end(value: date, offset: int) -> date:
    anchor = _quarter_end(value)
    q_index = anchor.year * 4 + ((anchor.month - 1) // 3) + offset
    year, quarter = divmod(q_index, 4)
    month = quarter * 3 + 3
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def _row_version_key(row: dict) -> tuple:
    # Legacy core.financials_quarterly has no published_at. Use its available
    # report/t0 trace deterministically instead of physical row order.
    return (
        row.get("t0_date") or row.get("report_date") or date.min,
        str(row.get("version_tag") or ""),
    )


class QuarterSeries:
    def __init__(self, rows: List[dict]):
        selected: dict[date, dict] = {}
        for row in rows:
            pe = row.get("period_end")
            if not isinstance(pe, date) or isinstance(pe, datetime):
                raise ValueError("QuarterSeries period_end date olmali")
            pe = _quarter_end(pe)
            previous = selected.get(pe)
            if previous is None or _row_version_key(row) > _row_version_key(previous):
                selected[pe] = row
        self.by_period = selected
        self.rows = [selected[pe] for pe in sorted(selected)]

    def get(self, pe: date, field: str):
        row = self.by_period.get(_quarter_end(pe))
        return None if row is None else row.get(field)

    def lag(self, pe: date, field: str, n: int):
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            return None
        return self.get(_shift_quarter_end(pe, -n), field)

    def avg(self, pe: date, field: str):
        x0 = self.get(pe, field)
        x1 = self.lag(pe, field, 1)
        if x0 is None and x1 is None:
            return None
        if x0 is None:
            return x1
        if x1 is None:
            return x0
        return (x0 + x1) / 2.0

    def sum4q(self, pe: date, field: str):
        vals = []
        for offset in (-3, -2, -1, 0):
            v = self.get(_shift_quarter_end(pe, offset), field)
            if v is None:
                return None
            vals.append(float(v))
        return float(sum(vals))

    def days_in_period(self, pe: date) -> int:
        current = _quarter_end(pe)
        previous = _shift_quarter_end(current, -1)
        if previous not in self.by_period:
            return 91
        d = (current - previous).days
        return int(d) if 60 <= d <= 120 else 91


def safe_eval_expr(expr: str, env: dict, qs: QuarterSeries, pe: date):
    tree = ast.parse(expr, mode="eval")

    def eval_node(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            v = eval_node(node.operand)
            return None if v is None else OPS[type(node.op)](v)
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            a, b = eval_node(node.left), eval_node(node.right)
            if a is None or b is None:
                return None
            if isinstance(node.op, ast.Div) and float(b) == 0.0:
                return None
            return OPS[type(node.op)](a, b)
        if isinstance(node, ast.Call):
            fn = node.func.id if isinstance(node.func, ast.Name) else None
            if fn not in ALLOWED_FUNCS:
                raise ValueError(f"Function not allowed: {fn}")
            if fn in {"avg", "lag", "lag4q", "sum4q", "ttm"}:
                if len(node.args) < 1:
                    return None
                a0 = node.args[0]
                field = a0.id if isinstance(a0, ast.Name) else (a0.value if isinstance(a0, ast.Constant) and isinstance(a0.value, str) else None)
                if not field:
                    return None
                if fn == "avg":
                    return qs.avg(pe, field)
                if fn == "lag":
                    if len(node.args) < 2:
                        return None
                    n = eval_node(node.args[1])
                    return None if n is None else qs.lag(pe, field, int(n))
                if fn == "lag4q":
                    return qs.lag(pe, field, 4)
                return qs.sum4q(pe, field)
            args = [eval_node(a) for a in node.args]
            if fn == "abs":
                return None if args[0] is None else abs(float(args[0]))
            if fn == "coalesce":
                return coalesce(*args)
            if fn == "nz":
                return nz(args[0], 0 if len(args) == 1 else args[1])
            if fn == "days_in_period":
                return qs.days_in_period(pe)
            if fn == "log":
                return None if args[0] is None or args[0] <= 0 else math.log(float(args[0]))
            if fn == "log1p":
                return None if args[0] is None else math.log1p(float(args[0]))
            if fn == "max":
                aa = [a for a in args if a is not None]
                return None if not aa else float(max(aa))
            if fn == "min":
                aa = [a for a in args if a is not None]
                return None if not aa else float(min(aa))
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    return eval_node(tree.body)


def safe_eval_condition(cond: str, env: dict, qs: QuarterSeries, pe: date) -> bool:
    s = cond.strip().replace(" is not null", " is not None").replace(" is null", " is None")
    tree = ast.parse(s, mode="eval")

    def eval_node(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not bool(eval_node(node.operand))
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(bool(eval_node(v)) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(bool(eval_node(v)) for v in node.values)
        if isinstance(node, ast.Compare):
            left = eval_node(node.left)
            for op_node, comp in zip(node.ops, node.comparators):
                right = eval_node(comp)
                op_type = type(op_node)
                if op_type in (ast.Is, ast.IsNot):
                    ok = CMP[op_type](left, right)
                else:
                    ok = False if left is None or right is None else CMP[op_type](left, right)
                if not ok:
                    return False
                left = right
            return True
        if isinstance(node, (ast.Call, ast.BinOp, ast.UnaryOp)):
            return safe_eval_expr(ast.unparse(node), env, qs, pe)
        return bool(eval_node(node))

    return bool(eval_node(tree.body))


def derive_fields_per_ticker(rows: List[dict]) -> List[dict]:
    for r in rows:
        if r.get("gross_profit") is None:
            rev, cogs = r.get("revenue"), r.get("cogs")
            if rev is not None and cogs is not None:
                r["gross_profit"] = rev - cogs
    return rows
