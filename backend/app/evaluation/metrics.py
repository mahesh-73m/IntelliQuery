"""Metric definitions. All numbers are computed from real executions; nothing is hard-coded."""
import re
from itertools import combinations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.query_executor import QueryResult

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ].*)?$")


def _norm(v) -> str:
    if v is None:
        return "None"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return f"{round(float(v), 2):.2f}"
    s = str(v).strip()
    return s[:10] if _DATE.match(s) else s


def _rows(rows: list[list], cols: tuple[int, ...] | None = None) -> list[tuple]:
    sel = (lambda r: [r[i] for i in cols]) if cols is not None else (lambda r: r)
    return [tuple(sorted(_norm(v) for v in sel(r))) for r in rows]  # column-order tolerant


def results_match(gold: "QueryResult", got: "QueryResult", ordered: bool) -> bool:
    """Execution-accuracy comparison: floats rounded to 2dp, dates compared by day, column order and
    column names ignored. If the answer has extra columns, any projection onto the gold's width may match."""
    if gold.row_count != got.row_count:
        return False
    g_cols, a_cols = len(gold.columns), len(got.columns)
    if a_cols < g_cols:
        return False
    gold_rows = _rows(gold.rows)
    finish = (lambda x: x) if ordered else sorted
    gold_rows = finish(gold_rows)
    if a_cols == g_cols:
        return finish(_rows(got.rows)) == gold_rows
    if a_cols > 8:
        return False
    return any(finish(_rows(got.rows, c)) == gold_rows for c in combinations(range(a_cols), g_cols))


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def aggregate(records: list[dict]) -> dict:
    n = len(records)
    exec_ok = [r for r in records if r["executed"]]
    asked = [r for r in records if r["asked"]]
    clear = [r for r in records if not r["expect_clarification"]]
    amb = [r for r in records if r["expect_clarification"]]
    times = [r["exec_ms"] for r in exec_ok if r["exec_ms"] is not None]
    return {
        "n": n,
        "execution_accuracy": _rate(sum(r["correct"] for r in records), n),
        "successful_query_rate": _rate(len(exec_ok), n),
        "clarification_rate": _rate(len(asked), n),
        "false_clarification_rate": _rate(sum(r["asked"] for r in clear), len(clear)),
        "missed_ambiguity_rate": _rate(sum(not r["asked"] for r in amb), len(amb)),
        "clarification_resolution_rate": _rate(sum(r["correct"] for r in asked), len(asked)),
        "avg_execution_ms": round(sum(times) / len(times), 2) if times else None,
        "failed_count": n - len(exec_ok),
    }
