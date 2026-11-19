"""AST-based SQL validation. The LLM's SQL is never trusted.

Checks (all must pass):
  1. Parses as PostgreSQL and contains exactly ONE statement.
  2. Root is a SELECT / set-operation (UNION...). WITH ... SELECT is allowed.
  3. No write/DDL/command/INTO/locking node anywhere in the tree.
  4. Every table is in the business-schema allowlist (no pg_catalog, no app schema,
     no table-valued functions).
  5. Every referenced column exists on the table it is qualified with / on some referenced table.
  6. No dangerous functions (pg_sleep, pg_read_file, dblink, set_config, lo_*, ...).
  7. Row cap: LIMIT is forced to <= max_rows.
Returns the normalized SQL string that will actually be executed.
"""
import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from app.core.exceptions import SQLValidationError

ALLOWED_SCHEMA = "business"

_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Drop", "Alter", "AlterTable", "Create", "Command", "Copy", "Merge",
    "TruncateTable", "Set", "Use", "Into", "Lock", "Grant", "Revoke", "Commit", "Rollback", "Transaction",
    "Pragma", "Analyze", "Kill", "LoadData", "Attach", "Detach",
]
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))

_SET_OPS = tuple(getattr(exp, n) for n in ("SetOperation", "Union", "Intersect", "Except") if hasattr(exp, n))

DENIED_FUNCTIONS = {
    "pg_sleep", "pg_sleep_for", "pg_sleep_until", "pg_read_file", "pg_read_binary_file", "pg_ls_dir",
    "pg_terminate_backend", "pg_cancel_backend", "pg_reload_conf", "pg_stat_file", "pg_advisory_lock",
    "set_config", "current_setting", "lo_import", "lo_export", "lo_open", "lo_get", "dblink", "dblink_exec",
    "query_to_xml", "table_to_xml", "database_to_xml", "xpath", "version", "current_user", "session_user",
    "inet_server_addr", "inet_client_addr", "txid_current", "generate_series_unbounded",
}
DENIED_PREFIXES = ("pg_", "lo_", "dblink", "txid_")


class ValidatedSQL(str):
    """Marker type: a str that has passed validate_sql()."""


def _fail(msg: str):
    raise SQLValidationError(msg)


def validate_sql(sql: str, schema: dict[str, set[str]], max_rows: int) -> ValidatedSQL:
    """`schema` maps table name -> set of column names (business schema only)."""
    if not sql or not sql.strip():
        _fail("The query is empty.")
    text = sql.strip().rstrip(";").strip()
    if len(text) > 8000:
        _fail("The query is too long.")

    try:
        statements = [s for s in sqlglot.parse(text, read="postgres") if s is not None]
    except SqlglotError as e:
        _fail(f"The SQL could not be parsed: {str(e).splitlines()[0][:200]}")
    if len(statements) != 1:
        _fail("Only a single SQL statement is allowed.")
    root = statements[0]

    if not isinstance(root, (exp.Select,) + _SET_OPS):
        _fail("Only SELECT queries are allowed.")

    for node in root.walk():
        if isinstance(node, FORBIDDEN_NODES):
            _fail(f"Statement type '{type(node).__name__.upper()}' is not allowed. Only read-only SELECT queries are permitted.")

    cte_names = {c.alias_or_name.lower() for c in root.find_all(exp.CTE)}
    derived = {s.alias_or_name.lower() for s in root.find_all(exp.Subquery) if s.alias_or_name}
    derived |= cte_names

    allowed = {t.lower(): {c.lower() for c in cols} for t, cols in schema.items()}
    alias_to_table: dict[str, str] = {}
    referenced: set[str] = set()

    for t in root.find_all(exp.Table):
        name = (t.name or "").lower()
        if not name or not isinstance(t.this, exp.Identifier):
            _fail("Table-valued functions are not allowed.")
        if t.catalog:
            _fail("Cross-database references are not allowed.")
        if name in cte_names and not t.db:
            derived.add((t.alias_or_name or name).lower())  # e.g. FROM rev r  -> r.col is fine
            continue
        if t.db and t.db.lower() != ALLOWED_SCHEMA:
            _fail(f"Schema '{t.db}' is not accessible.")
        if name not in allowed:
            _fail(f"Unknown table '{t.name}'. Available tables: {', '.join(sorted(allowed))}.")
        referenced.add(name)
        alias_to_table[(t.alias_or_name or name).lower()] = name
        alias_to_table.setdefault(name, name)

    if not referenced and not cte_names:
        _fail("The query must read from at least one table.")

    select_aliases = {a.alias.lower() for a in root.find_all(exp.Alias) if a.alias}
    for ta in root.find_all(exp.TableAlias):
        select_aliases |= {c.name.lower() for c in ta.columns}
    all_columns = set().union(*(allowed[t] for t in referenced)) if referenced else set()

    for col in root.find_all(exp.Column):
        if isinstance(col.this, exp.Star):
            continue
        cname, qualifier = col.name.lower(), (col.table or "").lower()
        if qualifier:
            if qualifier in alias_to_table:
                if cname not in allowed[alias_to_table[qualifier]]:
                    _fail(f"Unknown column '{col.table}.{col.name}'. Columns of {alias_to_table[qualifier]}: "
                          f"{', '.join(sorted(allowed[alias_to_table[qualifier]]))}.")
            elif qualifier not in derived:
                _fail(f"Unknown table or alias '{col.table}'.")
        elif cname not in all_columns and cname not in select_aliases:
            _fail(f"Unknown column '{col.name}'.")

    for fn in root.find_all(exp.Func):
        name = (fn.name if isinstance(fn, exp.Anonymous) else fn.sql_name()).lower()
        if name in DENIED_FUNCTIONS or name.startswith(DENIED_PREFIXES):
            _fail(f"Function '{name}' is not allowed.")

    return ValidatedSQL(_cap_rows(root, max_rows).sql(dialect="postgres"))


def _cap_rows(root: exp.Expression, max_rows: int) -> exp.Expression:
    if isinstance(root, exp.Select):
        limit = root.args.get("limit")
        expr = limit.expression if limit is not None else None
        if isinstance(expr, exp.Literal) and expr.is_int and int(expr.name) <= max_rows:
            return root
        return root.limit(max_rows)
    return exp.select("*").from_(root.subquery("_q")).limit(max_rows)
