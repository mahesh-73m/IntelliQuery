from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.exceptions import ExecutionError, NotFound, SQLValidationError
from app.database.session import get_db
from app.models.models import Conversation, Message, QueryHistory, SavedQuery, User
from app.schemas.api import ExecuteIn, SavedQueryIn
from app.security.rate_limit import rate_limit
from app.security.sql_validator import validate_sql
from app.services.chart_advisor import advise
from app.services.orchestrator import STORED_ROWS
from app.services.query_executor import execute_select
from app.services.schema_inspector import get_schema

router = APIRouter(prefix="/query", tags=["query"])


def _qh_out(q: QueryHistory) -> dict:
    return {"id": q.id, "conversation_id": q.conversation_id, "question": q.question, "sql": q.generated_sql,
            "status": q.status, "execution_time_ms": float(q.execution_time_ms) if q.execution_time_ms is not None else None,
            "row_count": q.row_count, "error": q.error_message, "was_clarified": q.was_clarified,
            "attempts": q.attempts, "created_at": q.created_at.isoformat()}


@router.post("/execute", dependencies=[Depends(rate_limit("exec"))])
def execute(body: ExecuteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Run SQL the user reviewed/edited. Goes through exactly the same validator and read-only engine."""
    conv = None
    if body.conversation_id is not None:
        conv = db.get(Conversation, body.conversation_id)
        if conv is None or conv.user_id != user.id:
            raise NotFound("Conversation not found")
    try:
        valid = validate_sql(body.sql, get_schema().column_map(), get_settings().max_result_rows)
        res = execute_select(valid)
    except (SQLValidationError, ExecutionError) as e:
        db.add(QueryHistory(user_id=user.id, conversation_id=conv.id if conv else None, question=body.question,
                            generated_sql=body.sql, status="error", error_message=e.message))
        db.commit()
        raise
    qh = QueryHistory(user_id=user.id, conversation_id=conv.id if conv else None, question=body.question,
                      generated_sql=str(valid), status="success", execution_time_ms=res.execution_time_ms,
                      row_count=res.row_count)
    db.add(qh)
    db.flush()
    out = {"sql": str(valid), "columns": res.columns, "rows": res.rows, "row_count": res.row_count,
           "truncated": res.truncated, "execution_time_ms": res.execution_time_ms,
           "chart": advise(res.columns, res.rows), "query_history_id": qh.id}
    if conv:
        db.add(Message(conversation_id=conv.id, role="assistant", content="Ran edited SQL.", payload={
            "type": "result", "question": body.question, "sql": str(valid), "edited": True,
            "summary": f"Ran your edited query: {res.row_count} row(s).", "explanation": "", "tables_used": [],
            "columns": res.columns, "rows": res.rows[:STORED_ROWS], "row_count": res.row_count,
            "truncated": res.truncated, "execution_time_ms": res.execution_time_ms, "chart": out["chart"],
            "assumptions": [], "slots": [], "attempts": 1, "query_history_id": qh.id}))
    db.commit()
    return out


@router.get("/history")
def history(status: str | None = Query(None, pattern="^(success|error)$"), limit: int = Query(50, ge=1, le=200),
            offset: int = Query(0, ge=0), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(QueryHistory).where(QueryHistory.user_id == user.id)
    if status:
        stmt = stmt.where(QueryHistory.status == status)
    rows = db.execute(stmt.order_by(QueryHistory.id.desc()).limit(limit).offset(offset)).scalars().all()
    return [_qh_out(q) for q in rows]


@router.get("/saved")
def list_saved(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(SavedQuery).where(SavedQuery.user_id == user.id).order_by(SavedQuery.id.desc())).scalars().all()
    return [{"id": s.id, "name": s.name, "question": s.question, "sql": s.sql_text, "created_at": s.created_at.isoformat()} for s in rows]


@router.post("/saved", status_code=201)
def save_query(body: SavedQueryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    validate_sql(body.sql, get_schema().column_map(), get_settings().max_result_rows)  # never store unsafe SQL
    s = SavedQuery(user_id=user.id, name=body.name.strip(), question=body.question, sql_text=body.sql)
    db.add(s)
    db.commit()
    return {"id": s.id, "name": s.name}


@router.delete("/saved/{saved_id}", status_code=204)
def delete_saved(saved_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(SavedQuery, saved_id)
    if s is None or s.user_id != user.id:
        raise NotFound("Saved query not found")
    db.delete(s)
    db.commit()


@router.get("/{query_id}")
def get_query(query_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.get(QueryHistory, query_id)
    if q is None or q.user_id != user.id:
        raise NotFound("Query not found")
    return _qh_out(q)
