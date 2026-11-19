"""Pydantic models for STRUCTURED LLM output. Every LLM answer is validated against these."""
from typing import Literal

from pydantic import BaseModel, Field


class Ambiguity(BaseModel):
    slot: Literal["metric", "time_period", "sort", "filter", "other"] = "other"
    term: str = ""
    question: str = ""
    options: list[str] = Field(default_factory=list)


class Understanding(BaseModel):
    intent: str = "unknown"
    entity: str | None = None
    metric: str | None = None
    time_period: str | None = None
    limit: int | None = None
    group_by: str | None = None
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    requires_clarification: bool = False


class GeneratedSQL(BaseModel):
    sql: str = ""
    explanation: str = ""
    tables_used: list[str] = Field(default_factory=list)
    requires_clarification: bool = False
