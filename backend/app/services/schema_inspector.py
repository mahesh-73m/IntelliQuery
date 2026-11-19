"""Automatic schema discovery for the `business` schema (tables, columns, PK/FK, sample values).

Only what the LLM needs is exposed. Results are cached for a few minutes.
"""
import time
from dataclasses import dataclass, field

from sqlalchemy import inspect, text

from app.database.engines import readonly_engine

SCHEMA = "business"
_TTL = 300
_cache: tuple[float, "SchemaInfo"] | None = None


@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    samples: list[str] = field(default_factory=list)  # distinct values for low-cardinality text columns


@dataclass
class TableInfo:
    name: str
    columns: list[ColumnInfo]
    primary_key: list[str]
    foreign_keys: list[dict]  # {"columns": [...], "ref_table": str, "ref_columns": [...]}


@dataclass
class SchemaInfo:
    tables: dict[str, TableInfo]

    def column_map(self) -> dict[str, set[str]]:
        return {t: {c.name for c in info.columns} for t, info in self.tables.items()}

    def to_prompt(self, only: set[str] | None = None) -> str:
        lines = []
        for name, t in self.tables.items():
            if only and name not in only:
                continue
            cols = []
            for c in t.columns:
                tag = " PK" if c.name in t.primary_key else ""
                s = f" values={c.samples}" if c.samples else ""
                cols.append(f"{c.name} {c.type}{tag}{'' if c.nullable else ' NOT NULL'}{s}")
            lines.append(f"TABLE {name} (" + ", ".join(cols) + ")")
        for name, t in self.tables.items():
            if only and name not in only:
                continue
            for fk in t.foreign_keys:
                lines.append(f"FK {name}.{','.join(fk['columns'])} -> {fk['ref_table']}.{','.join(fk['ref_columns'])}")
        return "\n".join(lines)

    def to_public(self) -> dict:
        return {
            n: {
                "columns": [{"name": c.name, "type": c.type, "nullable": c.nullable,
                             "primary_key": c.name in t.primary_key, "samples": c.samples} for c in t.columns],
                "foreign_keys": t.foreign_keys,
            }
            for n, t in self.tables.items()
        }


def _samples(conn, table: str, column: str) -> list[str]:
    q = conn.dialect.identifier_preparer.quote
    rows = conn.execute(text(f"SELECT DISTINCT {q(column)} FROM {q(SCHEMA)}.{q(table)} "
                             f"WHERE {q(column)} IS NOT NULL ORDER BY 1 LIMIT 11")).fetchall()
    vals = [str(r[0]) for r in rows]
    return vals if len(vals) <= 10 else []


def get_schema(force: bool = False) -> SchemaInfo:
    global _cache
    if _cache and not force and time.time() - _cache[0] < _TTL:
        return _cache[1]
    insp = inspect(readonly_engine)
    tables: dict[str, TableInfo] = {}
    with readonly_engine.connect() as conn:
        for tname in sorted(insp.get_table_names(schema=SCHEMA)):
            pk = insp.get_pk_constraint(tname, schema=SCHEMA).get("constrained_columns", [])
            cols = []
            for c in insp.get_columns(tname, schema=SCHEMA):
                ctype = str(c["type"]).lower()
                info = ColumnInfo(c["name"], ctype, bool(c["nullable"]))
                if "char" in ctype or ctype == "text":
                    info.samples = _samples(conn, tname, c["name"])
                cols.append(info)
            fks = [{"columns": fk["constrained_columns"], "ref_table": fk["referred_table"],
                    "ref_columns": fk["referred_columns"]} for fk in insp.get_foreign_keys(tname, schema=SCHEMA)]
            tables[tname] = TableInfo(tname, cols, pk, fks)
    info = SchemaInfo(tables)
    _cache = (time.time(), info)
    return info
