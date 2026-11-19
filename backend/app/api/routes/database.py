import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine.url import make_url

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.database.engines import readonly_engine
from app.models.models import User
from app.services.schema_inspector import get_schema

router = APIRouter(prefix="/database", tags=["database"])


@router.get("/schema")
def schema(_: User = Depends(get_current_user)):
    return {"schema": "business", "tables": get_schema().to_public()}


@router.get("/status")
def status(_: User = Depends(get_current_user)):
    """Connectivity check. Never returns credentials; host/database are shown without the password."""
    url = make_url(get_settings().readonly_database_url)
    start = time.perf_counter()
    try:
        with readonly_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ok = True
    except Exception:  # noqa: BLE001 - report, don't leak
        ok = False
    return {"connected": ok, "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            "host": url.host, "database": url.database, "role": url.username, "read_only": True,
            "tables": len(get_schema().tables) if ok else 0}
