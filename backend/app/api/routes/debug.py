"""Stage-by-stage endpoints (the original understand / clarify / generate-sql split), kept for
debugging and for demonstrating each module in isolation. They NEVER execute SQL."""
from fastapi import APIRouter, Depends

from app.ai import pipeline
from app.ai.clarification.detector import detect
from app.ai.providers import get_provider
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.exceptions import SQLValidationError
from app.models.models import User
from app.schemas.api import DebugQuestion
from app.security.rate_limit import rate_limit
from app.security.sql_validator import validate_sql
from app.services.schema_inspector import get_schema
from app.services.schema_linker import link_schema

router = APIRouter(prefix="/debug", tags=["debug"], dependencies=[Depends(rate_limit("debug"))])


@router.post("/understand")
def understand(body: DebugQuestion, _: User = Depends(get_current_user)):
    text = link_schema(body.question, get_schema())
    return pipeline.understand(get_provider(body.provider), body.question, text)


@router.post("/clarify")
def clarify(body: DebugQuestion, _: User = Depends(get_current_user)):
    """Rule-based ambiguity check only (no LLM call)."""
    pending = [c for c in detect(body.question) if c.id not in body.confirmed]
    return {"requires_clarification": bool(pending), "next_question": pending[0].public() if pending else None,
            "remaining": [c.id for c in pending[1:]]}


@router.post("/generate-sql")
def generate(body: DebugQuestion, _: User = Depends(get_current_user)):
    schema = get_schema()
    confirmed = {}
    for c in detect(body.question):
        opt_id = body.confirmed.get(c.id)
        opt = next((o for o in c.options if o["id"] == opt_id), None)
        if opt is None:
            return {"requires_clarification": True, "next_question": c.public()}
        confirmed[c.id] = {"instruction": opt["instruction"], "label": opt["label"]}
    gen = pipeline.generate_sql(get_provider(body.provider), body.question, link_schema(body.question, schema), confirmed)
    try:
        valid = str(validate_sql(gen.sql, schema.column_map(), get_settings().max_result_rows))
        return {**gen.model_dump(), "sql": valid, "valid": True, "validation_error": None, "requires_clarification": False}
    except SQLValidationError as e:
        return {**gen.model_dump(), "valid": False, "validation_error": e.message}
