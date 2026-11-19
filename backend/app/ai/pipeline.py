"""LLM-facing pipeline steps, independent of HTTP and of persistence (reused by the evaluation harness)."""
import json
import logging
from dataclasses import dataclass
from typing import Callable

from pydantic import ValidationError

from app.ai import prompts
from app.ai.providers.base import LLMProvider
from app.ai.semantic.loader import glossary_text, load_catalog
from app.core.config import get_settings
from app.core.exceptions import ExecutionError, LLMError, SQLValidationError
from app.schemas.llm import GeneratedSQL, Understanding
from app.security.sql_validator import validate_sql
from app.services.query_executor import QueryResult, execute_select
from app.services.schema_inspector import SchemaInfo

log = logging.getLogger(__name__)


def _history_text(history: list[dict] | None) -> str:
    if not history:
        return "(none)"
    return "\n".join(f"Q: {h['question']}\nSQL: {h.get('sql') or '(none)'}" for h in history[-3:])


def understand(provider: LLMProvider, question: str, schema_text: str, history: list[dict] | None = None) -> dict:
    user = (f"SCHEMA:\n{schema_text}\n\nGLOSSARY & DEFAULTS:\n{glossary_text(load_catalog())}\n\n"
            f"Previous conversation:\n{_history_text(history)}\n\nQUESTION: {question}")
    try:
        return Understanding.model_validate(provider.complete_json(prompts.UNDERSTAND_SYSTEM, user)).model_dump()
    except ValidationError:
        log.warning("understanding output failed validation; continuing without it")
        return Understanding().model_dump()


def _confirmed_text(confirmed: dict) -> str:
    if not confirmed:
        return "(none)"
    return "\n".join(f"- {c['instruction']}" for c in confirmed.values())


def generate_sql(provider: LLMProvider, question: str, schema_text: str, confirmed: dict,
                 history: list[dict] | None = None, feedback: str | None = None) -> GeneratedSQL:
    user = (f"SCHEMA:\n{schema_text}\n\nGLOSSARY & DEFAULTS:\n{glossary_text(load_catalog())}\n\n"
            f"USER-CONFIRMED INTERPRETATIONS:\n{_confirmed_text(confirmed)}\n\n"
            f"Previous conversation:\n{_history_text(history)}\n\nQUESTION: {question}")
    if feedback:
        user += f"\n\nYour previous attempt failed. Fix it.\n{feedback}"
    try:
        return GeneratedSQL.model_validate(provider.complete_json(prompts.GENERATE_SYSTEM, user))
    except ValidationError:
        raise LLMError("The AI returned a malformed SQL response.")


def basic_generate(provider: LLMProvider, question: str, schema_text: str) -> GeneratedSQL:
    """Baseline system A: question + schema only. No glossary, no clarification."""
    user = f"SCHEMA:\n{schema_text}\n\nQUESTION: {question}"
    try:
        return GeneratedSQL.model_validate(provider.complete_json(prompts.BASIC_SYSTEM, user))
    except ValidationError:
        raise LLMError("The AI returned a malformed SQL response.")


@dataclass
class Outcome:
    sql: str = ""
    explanation: str = ""
    tables_used: list[str] | None = None
    result: QueryResult | None = None
    attempts: int = 0
    error: str | None = None


def generate_and_execute(provider: LLMProvider, question: str, schema: SchemaInfo, schema_text: str,
                         confirmed: dict, history: list[dict] | None = None, max_retries: int = 2,
                         on_phase: Callable[[str], None] | None = None) -> Outcome:
    """Generate -> validate -> execute, feeding errors back to the LLM up to `max_retries` times."""
    phase = on_phase or (lambda _p: None)
    out = Outcome()
    feedback = None
    for attempt in range(1, max_retries + 2):
        out.attempts = attempt
        phase("GENERATING")
        gen = generate_sql(provider, question, schema_text, confirmed, history, feedback)
        out.sql, out.explanation, out.tables_used = gen.sql, gen.explanation, gen.tables_used
        if not gen.sql.strip():
            out.error = "The AI could not produce a query for this question. Try rephrasing it."
            feedback = "You returned no SQL. Return a SELECT query."
            continue
        try:
            phase("VALIDATING")
            valid = validate_sql(gen.sql, schema.column_map(), get_settings().max_result_rows)
            out.sql = str(valid)
            phase("EXECUTING")
            out.result = execute_select(valid)
            out.error = None
            return out
        except (SQLValidationError, ExecutionError) as e:
            detail = getattr(e, "detail", "")
            out.error = e.message
            feedback = f"Previous SQL:\n{gen.sql}\nError: {e.message} {detail}".strip()
            log.info("attempt %d failed: %s %s", attempt, e.message, detail)
    return out


def summarize(provider: LLMProvider, question: str, sql: str, result: QueryResult) -> str | None:
    """Short natural-language summary. Receives only a small sample of rows (injection hygiene)."""
    if result.row_count == 0:
        return "The query ran successfully but returned no rows."
    sample = {"question": question, "columns": result.columns, "row_count": result.row_count,
              "truncated": result.truncated, "first_rows": result.rows[:10]}
    try:
        data = provider.complete_json(prompts.SUMMARY_SYSTEM, "SQL:\n" + sql + "\n\nRESULT:\n" + json.dumps(sample, default=str))
        s = data.get("summary")
        return s.strip() if isinstance(s, str) and s.strip() else None
    except LLMError:
        return None
