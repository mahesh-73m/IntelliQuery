"""Chooses a sensible chart from the shape of a result set (pure Python, no dependencies)."""
import re

DATE_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?([T ]\d{2}:\d{2}.*)?$")
TIME_WORDS = ("date", "day", "week", "month", "year", "quarter", "time", "period")


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def advise(columns: list[str], rows: list[list]) -> dict:
    none = {"recommended": "table", "options": [], "x": None, "y": []}
    if len(rows) < 2 or len(columns) < 2:
        return none
    sample = rows[:200]
    numeric, textual = [], []
    for i, name in enumerate(columns):
        vals = [r[i] for r in sample if r[i] is not None]
        if vals and all(_is_num(v) for v in vals):
            numeric.append(i)
        else:
            textual.append(i)
    if not numeric:
        return none

    def looks_temporal(i: int) -> bool:
        vals = [r[i] for r in sample if r[i] is not None]
        by_value = bool(vals) and all(isinstance(v, str) and DATE_RE.match(v) for v in vals)
        by_name = any(w in columns[i].lower() for w in TIME_WORDS)
        return by_value or (by_name and not _is_num(vals[0]) if vals else False)

    x_idx = next((i for i in textual if looks_temporal(i)), None)
    temporal = x_idx is not None
    if x_idx is None:
        x_idx = textual[0] if textual else numeric[0]
    y_idx = [i for i in numeric if i != x_idx][:3]
    if not y_idx:
        return none

    if temporal:
        rec, opts = "line", ["line", "area", "bar"]
    elif len(rows) <= 8 and len(y_idx) == 1 and all((r[y_idx[0]] or 0) >= 0 for r in rows):
        rec, opts = "pie", ["pie", "bar", "line", "area"]
    else:
        rec, opts = "bar", ["bar", "line", "area"] + (["pie"] if len(y_idx) == 1 and len(rows) <= 12 else [])
    return {"recommended": rec, "options": opts, "x": columns[x_idx], "y": [columns[i] for i in y_idx]}
