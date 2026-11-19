"""Executes validated SQL on the read-only engine and returns JSON-safe results."""
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dtime
from decimal import Decimal

from psycopg import errors as pgerr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.exceptions import ExecutionError
from app.database.engines import readonly_engine
from app.security.sql_validator import ValidatedSQL

log = logging.getLogger(__name__)


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list]
    row_count: int
    truncated: bool
    execution_time_ms: float


def _json_safe(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date, dtime)):
        return v.isoformat()
    if isinstance(v, (bytes, memoryview)):
        return "<binary>"
    if isinstance(v, (list, tuple, set)):
        return [_json_safe(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _json_safe(x) for k, x in v.items()}
    return v


def _friendly(e: DBAPIError) -> tuple[str, str]:
    orig = e.orig
    detail = str(orig).splitlines()[0][:300] if orig else "database error"
    s = get_settings()
    if isinstance(orig, pgerr.QueryCanceled):
        return f"The query took longer than {s.query_timeout_seconds} seconds and was stopped. Try narrowing it.", detail
    if isinstance(orig, pgerr.InsufficientPrivilege):
        return "That query touches data you are not permitted to read.", detail
    if isinstance(orig, (pgerr.UndefinedTable, pgerr.UndefinedColumn)):
        return "The query references a table or column that does not exist.", detail
    if isinstance(orig, pgerr.SyntaxError):
        return "The query has a syntax error.", detail
    if isinstance(orig, pgerr.DivisionByZero):
        return "The query divided by zero.", detail
    return "The database could not run this query.", detail


def execute_select(sql: ValidatedSQL) -> QueryResult:
    if not isinstance(sql, ValidatedSQL):
        raise ExecutionError("Refusing to run SQL that was not validated.")
    s = get_settings()
    start = time.perf_counter()
    try:
        with readonly_engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            # colons must be escaped for text(); they appear in ::casts and string literals
            result = conn.execute(text(str(sql).replace(":", r"\:")))
            raw = result.fetchmany(s.max_result_rows + 1)
            columns = list(result.keys())
            conn.rollback()
    except DBAPIError as e:
        user_msg, detail = _friendly(e)
        log.warning("query failed: %s", detail)
        raise ExecutionError(user_msg, detail)
    elapsed = (time.perf_counter() - start) * 1000
    truncated = len(raw) > s.max_result_rows
    rows = [[_json_safe(v) for v in r] for r in raw[: s.max_result_rows]]
    return QueryResult(columns, rows, len(rows), truncated, round(elapsed, 2))
