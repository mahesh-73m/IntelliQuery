from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.models import ClarificationHistory, EvaluationMetric, QueryHistory, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = QueryHistory
    total, ok, avg_ms, clarified = db.execute(select(
        func.count(), func.count().filter(q.status == "success"), func.avg(q.execution_time_ms),
        func.count().filter(q.was_clarified))
        .where(q.user_id == user.id)).one()
    c = ClarificationHistory
    asked, resolved = db.execute(select(func.count(), func.count().filter(c.resolved)).where(c.user_id == user.id)).one()
    daily = db.execute(text(
        "SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day, count(*) AS total, "
        "count(*) FILTER (WHERE status='success') AS success FROM app.query_history "
        "WHERE user_id = :u AND created_at >= now() - interval '14 days' GROUP BY 1 ORDER BY 1"), {"u": user.id}).all()
    recent = db.execute(select(q).where(q.user_id == user.id).order_by(q.id.desc()).limit(6)).scalars().all()
    return {
        "total_queries": total, "successful_queries": ok, "failed_queries": total - ok,
        "success_rate": round(100 * ok / total, 1) if total else None,
        "avg_execution_ms": round(float(avg_ms), 2) if avg_ms is not None else None,
        "clarification_requests": asked, "clarifications_resolved": resolved,
        "clarification_resolution_rate": round(100 * resolved / asked, 1) if asked else None,
        "clarified_queries": clarified,
        "daily": [{"day": d, "total": t, "success": s} for d, t, s in daily],
        "recent": [{"id": r.id, "question": r.question, "status": r.status, "created_at": r.created_at.isoformat(),
                    "execution_time_ms": float(r.execution_time_ms) if r.execution_time_ms is not None else None} for r in recent],
    }


@router.get("/evaluation")
def evaluation(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Metrics from the most recent benchmark run (python -m app.evaluation.runner). Nothing is fabricated:
    if no run exists the response says so."""
    run = db.execute(select(EvaluationMetric.run_id, func.max(EvaluationMetric.created_at).label("t"))
                     .group_by(EvaluationMetric.run_id).order_by(text("t DESC")).limit(1)).first()
    if run is None:
        return {"run_id": None, "metrics": [], "message": "No evaluation has been run yet."}
    rows = db.execute(select(EvaluationMetric).where(EvaluationMetric.run_id == run.run_id)).scalars().all()
    return {"run_id": run.run_id, "created_at": run.t.isoformat(), "message": None,
            "metrics": [{"system": r.system, "category": r.category, "metric": r.metric_name,
                         "value": r.value, "details": r.details} for r in rows]}
