"""Deterministic (rule-based) ambiguity detection. No LLM, no database, fully unit-testable.

A candidate is produced when a vague phrase from the semantic layer is present AND the user has
not already made the choice explicit (`unless`) or supplied a time period (`unless_time_expr`).
"""
import re
from dataclasses import dataclass, field

from app.ai.semantic.loader import load_catalog


@dataclass
class Candidate:
    id: str
    slot: str
    question: str
    options: list[dict] = field(default_factory=list)  # {id, label, instruction}
    priority: int = 50
    source: str = "rule"  # "rule" | "llm"

    def public(self) -> dict:
        return {"id": self.id, "slot": self.slot, "question": self.question,
                "options": [{"id": o["id"], "label": o["label"]} for o in self.options]}

    def to_dict(self) -> dict:
        return {"id": self.id, "slot": self.slot, "question": self.question, "options": self.options,
                "priority": self.priority, "source": self.source}

    @classmethod
    def from_dict(cls, d: dict) -> "Candidate":
        return cls(**d)


_cache: dict[str, re.Pattern] = {}


def _rx(p: str) -> re.Pattern:
    if p not in _cache:
        _cache[p] = re.compile(p, re.IGNORECASE)
    return _cache[p]


def has_time_expression(question: str, catalog: dict | None = None) -> bool:
    cat = catalog or load_catalog()
    return bool(_rx(cat["time_expression_pattern"]).search(question))


def detect(question: str, catalog: dict | None = None) -> list[Candidate]:
    cat = catalog or load_catalog()
    timed = has_time_expression(question, cat)
    out: list[Candidate] = []
    for term in cat["ambiguous_terms"]:
        if not _rx(term["pattern"]).search(question):
            continue
        if term.get("unless") and _rx(term["unless"]).search(question):
            continue
        if term.get("unless_time_expr") and timed:
            continue
        out.append(Candidate(term["id"], term["slot"], term["question"], term["options"],
                             term.get("priority", 50)))
    out.sort(key=lambda c: c.priority)
    return out
