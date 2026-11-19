"""Schema linking: send the LLM only the tables relevant to the question.

With a small schema everything is sent. Above `SMALL_SCHEMA` tables we score tables by keyword
overlap with the question and add their foreign-key neighbours so JOIN paths stay available.
"""
import re

from app.services.schema_inspector import SchemaInfo

SMALL_SCHEMA = 8


def _stem(w: str) -> str:
    return re.sub(r"(ies|es|s)$", "", w.lower())


def link_schema(question: str, schema: SchemaInfo) -> str:
    if len(schema.tables) <= SMALL_SCHEMA:
        return schema.to_prompt()
    words = {_stem(w) for w in re.findall(r"[a-zA-Z]+", question)}
    chosen: set[str] = set()
    for name, t in schema.tables.items():
        tokens = {_stem(p) for p in name.split("_")} | {_stem(p) for c in t.columns for p in c.name.split("_")}
        if words & tokens:
            chosen.add(name)
    for name in list(chosen):
        for fk in schema.tables[name].foreign_keys:
            chosen.add(fk["ref_table"])
    return schema.to_prompt(chosen or None)
