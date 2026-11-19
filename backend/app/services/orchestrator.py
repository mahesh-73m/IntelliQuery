"""Orchestrates one conversational turn: clarification state machine -> SQL pipeline -> persistence.

The frontend never decides whether to run SQL; this module does. SQL is executed only after the
state machine reaches READY_TO_GENERATE (all required ambiguities resolved or the round cap hit).
"""
import copy
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import pipeline
from app.ai.clarification import state_machine as sm
from app.ai.clarification.detector import detect
from app.ai.providers import get_provider
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.models import ClarificationHistory, Conversation, Message, QueryHistory, User
from app.services.chart_advisor import advise
from app.services.schema_inspector import get_schema
from app.services.schema_linker import link_schema

log = logging.getLogger(__name__)
STORED_ROWS = 500


def _history(db: Session, conv: Conversation) -> list[dict]:
    rows = db.execute(select(Message).where(Message.conversation_id == conv.id, Message.role == "assistant")
                      .order_by(Message.id.desc()).limit(20)).scalars().all()
    out = [{"question": m.payload.get("question", ""), "sql": m.payload.get("sql")}
           for m in rows if m.payload.get("type") == "result"][:3]
    return list(reversed(out))


def _add_message(db: Session, conv: Conversation, role: str, content: str, payload: dict | None = None) -> Message:
    m = Message(conversation_id=conv.id, role=role, content=content, payload=payload or {})
    db.add(m)
    db.flush()
    return m


def message_out(m: Message) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "payload": m.payload,
            "created_at": m.created_at.isoformat() if m.created_at else None}


def result_payload(question: str, outcome, summary: str | None, state: dict, history_id: int | None) -> dict:
    r = outcome.result
    return {
        "type": "result", "question": question, "sql": outcome.sql, "explanation": outcome.explanation,
        "summary": summary or outcome.explanation, "tables_used": outcome.tables_used or [],
        "columns": r.columns, "rows": r.rows[:STORED_ROWS], "row_count": r.row_count,
        "truncated": r.truncated or r.row_count > STORED_ROWS, "execution_time_ms": r.execution_time_ms,
        "chart": advise(r.columns, r.rows), "attempts": outcome.attempts,
        "assumptions": state.get("assumptions", []), "slots": sm.build_slots(state), "query_history_id": history_id,
    }


def process_turn(db: Session, user: User, conv: Conversation, *, question: str | None = None,
                 option_id: str | None = None, provider_name: str | None = None) -> dict:
    settings = get_settings()
    state = copy.deepcopy(conv.state or {})
    provider_cache = {}

    def provider():
        if "p" not in provider_cache:
            provider_cache["p"] = get_provider(provider_name or (user.preferences or {}).get("provider"))
        return provider_cache["p"]

    # ---- 1. intake -------------------------------------------------------------------------
    if option_id is not None:
        pending = state.get("pending") or {}
        option = sm.apply_answer(state, option_id)  # raises 409/422 on invalid use
        _add_message(db, conv, "user", option["label"], {"type": "clarification_answer", "option_id": option_id})
        row = db.execute(select(ClarificationHistory).where(
            ClarificationHistory.conversation_id == conv.id, ClarificationHistory.term_id == pending.get("id"),
            ClarificationHistory.resolved.is_(False)).order_by(ClarificationHistory.id.desc()).limit(1)).scalar_one_or_none()
        if row:
            row.selected_option, row.resolved, row.resolved_at = option_id, True, datetime.now(timezone.utc)
        question = state["original_question"]
    else:
        memory = {k: v for k, v in (state.get("confirmed") or {}).items()
                  if v.get("source") in ("user_clarification", "memory")}
        state = sm.new_state(question, memory)
        _add_message(db, conv, "user", question)
        if conv.title == "New conversation":
            conv.title = question[:60]
        for c in detect(question):
            if c.id in memory:
                state["assumptions"].append(f"Using your earlier answer for “{c.question}”: {memory[c.id]['label']}.")

    schema = get_schema()
    schema_text = link_schema(question, schema)
    history = _history(db, conv)

    # ---- 2. clarification policy -----------------------------------------------------------------
    try:
        decision = sm.decide(state, settings.max_clarification_rounds,
                             lambda: pipeline.understand(provider(), question, schema_text, history))
        if decision.kind == "ask":
            cand = decision.candidate
            db.add(ClarificationHistory(user_id=user.id, conversation_id=conv.id, original_question=question,
                                        term_id=cand.id, question=cand.question, options=cand.public()["options"]))
            payload = {"type": "clarification", "question": question, "term_id": cand.id,
                       "prompt": cand.question, "options": cand.public()["options"], "round": state["rounds"],
                       "max_rounds": settings.max_clarification_rounds, "source": cand.source}
            msg = _add_message(db, conv, "assistant", cand.question, payload)
            return _finish(db, conv, state, msg, "clarification_needed")

        # ---- 3. generate -> validate -> execute -------------------------------------------------
        outcome = pipeline.generate_and_execute(provider(), question, schema, schema_text, state["confirmed"],
                                                history, on_phase=lambda p: sm.transition(state, p))
        if outcome.result is None:
            sm.transition(state, "FAILED")
            return _fail(db, user, conv, state, question, outcome.error or "The query could not be completed.",
                         outcome.sql, outcome.attempts)

        summary = pipeline.summarize(provider(), question, outcome.sql, outcome.result)
        sm.transition(state, "COMPLETED")
        qh = QueryHistory(user_id=user.id, conversation_id=conv.id, question=question, generated_sql=outcome.sql,
                          status="success", execution_time_ms=outcome.result.execution_time_ms,
                          row_count=outcome.result.row_count, was_clarified=state["was_clarified"],
                          attempts=outcome.attempts)
        db.add(qh)
        db.flush()
        payload = result_payload(question, outcome, summary, state, qh.id)
        msg = _add_message(db, conv, "assistant", payload["summary"], payload)
        return _finish(db, conv, state, msg, "completed")
    except AppError as e:  # LLM outage, bad key, ... : keep the conversation usable
        if e.status_code >= 500 or e.status_code == 400:
            state["phase"] = "FAILED"
            return _fail(db, user, conv, state, question, e.message, None, 0, record=False)
        raise


def _fail(db, user, conv, state, question, message, sql, attempts, record=True) -> dict:
    if record:
        db.add(QueryHistory(user_id=user.id, conversation_id=conv.id, question=question, generated_sql=sql or None,
                            status="error", error_message=message, was_clarified=state.get("was_clarified", False),
                            attempts=attempts))
    msg = _add_message(db, conv, "assistant", message, {"type": "error", "question": question, "message": message, "sql": sql})
    return _finish(db, conv, state, msg, "error")


def _finish(db: Session, conv: Conversation, state: dict, msg: Message, status: str) -> dict:
    conv.state = copy.deepcopy(state)
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": status, "message": message_out(msg)}
