"""Clarification state machine + policy ("should we ask?").

State is a plain dict persisted in app.conversations.state (JSONB), so conversations can be
resumed and earlier answers remembered.

    RECEIVED -> ANALYZING_AMBIGUITY -> AWAITING_USER -> ANALYZING_AMBIGUITY (loop, <= max rounds)
                                    -> READY_TO_GENERATE -> GENERATING -> VALIDATING -> EXECUTING
                                    -> COMPLETED | FAILED

Policy: ask only if (1) a vague term is detected, (2) the user did not already specify it,
(3) no safe default exists (the semantic layer only lists terms WITHOUT a safe default),
(4) not already answered earlier in this conversation, and (5) the round cap is not reached.
Questions are asked one at a time in priority order (metric -> filter -> time period).
"""
import zlib
from dataclasses import dataclass

from app.ai.clarification.detector import Candidate, detect
from app.core.exceptions import AppError

TRANSITIONS = {
    "IDLE": {"RECEIVED"},
    "RECEIVED": {"ANALYZING_AMBIGUITY"},
    "ANALYZING_AMBIGUITY": {"AWAITING_USER", "READY_TO_GENERATE"},
    "AWAITING_USER": {"ANALYZING_AMBIGUITY", "RECEIVED"},
    "READY_TO_GENERATE": {"GENERATING"},
    "GENERATING": {"VALIDATING", "FAILED"},
    "VALIDATING": {"EXECUTING", "GENERATING", "FAILED"},
    "EXECUTING": {"COMPLETED", "GENERATING", "FAILED"},
    "COMPLETED": {"RECEIVED"},
    "FAILED": {"RECEIVED"},
}
MAX_LLM_QUESTIONS = 1


def transition(state: dict, new_phase: str) -> None:
    cur = state.get("phase", "IDLE")
    if new_phase not in TRANSITIONS.get(cur, set()):
        raise AppError(f"Invalid state transition {cur} -> {new_phase}", 500)
    state["phase"] = new_phase


def new_state(question: str, memory: dict | None = None) -> dict:
    """Fresh state for a new user question. `memory` carries earlier clarification answers."""
    return {
        "phase": "RECEIVED",
        "original_question": question,
        "confirmed": {k: {**v, "source": "memory"} for k, v in (memory or {}).items()},
        "pending": None,
        "rounds": 0,
        "llm_questions": 0,
        "understanding": None,
        "assumptions": [],
        "was_clarified": False,
    }


@dataclass
class Decision:
    kind: str  # "ask" | "ready"
    candidate: Candidate | None = None


def llm_candidates(understanding: dict | None) -> list[Candidate]:
    """Convert ambiguities flagged by the LLM into candidates (lower priority than rules)."""
    if not understanding or not understanding.get("requires_clarification"):
        return []
    out = []
    for i, a in enumerate(understanding.get("ambiguities", [])):
        opts = [o for o in a.get("options", []) if o][:4]
        if len(opts) < 2:
            continue
        cid = f"llm_{i}_{zlib.crc32(a.get('term', '').encode()) % 10000}"
        out.append(Candidate(
            cid, a.get("slot", "other"), a.get("question") or f"What do you mean by '{a.get('term')}'?",
            [{"id": f"opt{j + 1}", "label": o, "instruction": f"Interpret '{a.get('term')}' as: {o}."}
             for j, o in enumerate(opts)], priority=90, source="llm"))
    return out


def decide(state: dict, max_rounds: int, understand_fn=None) -> Decision:
    """Run the policy. `understand_fn()` is called lazily (only when rules found nothing to ask)
    and must return the LLM understanding dict; it is cached in state."""
    transition(state, "ANALYZING_AMBIGUITY")
    question = state["original_question"]
    confirmed = state["confirmed"]

    pending = [c for c in detect(question) if c.id not in confirmed]
    if not pending and understand_fn and state["llm_questions"] < MAX_LLM_QUESTIONS:
        if state.get("understanding") is None:
            state["understanding"] = understand_fn()
        pending = [c for c in llm_candidates(state["understanding"]) if c.id not in confirmed]

    if pending and state["rounds"] < max_rounds:
        cand = pending[0]
        state["pending"] = cand.to_dict()
        state["rounds"] += 1
        if cand.source == "llm":
            state["llm_questions"] += 1
        transition(state, "AWAITING_USER")
        return Decision("ask", cand)

    for cand in pending:  # round cap reached: proceed with best guess and say so
        first = cand.options[0]
        confirmed[cand.id] = {"option_id": first["id"], "label": first["label"],
                              "instruction": first["instruction"], "source": "assumed"}
        state["assumptions"].append(f"Assumed {cand.question.rstrip('?').lower()}: {first['label'].lower()}.")
    state["pending"] = None
    transition(state, "READY_TO_GENERATE")
    return Decision("ready")


def apply_answer(state: dict, option_id: str) -> dict:
    """Merge the user's choice into confirmed slots. Returns the selected option."""
    if state.get("phase") != "AWAITING_USER" or not state.get("pending"):
        raise AppError("There is no clarification waiting for an answer.", 409)
    cand = state["pending"]
    option = next((o for o in cand["options"] if o["id"] == option_id), None)
    if option is None:
        raise AppError("That option is not valid for this question.", 422)
    state["confirmed"][cand["id"]] = {"option_id": option["id"], "label": option["label"],
                                      "instruction": option["instruction"], "source": "user_clarification"}
    state["was_clarified"] = True
    state["pending"] = None
    return option


def build_slots(state: dict) -> list[dict]:
    """Human-readable view of what the engine understood: value, status and provenance per slot."""
    und = state.get("understanding") or {}
    slots = []
    if und.get("entity"):
        slots.append({"name": "entity", "value": und["entity"], "status": "inferred", "source": "schema_inference"})
    confirmed = state.get("confirmed", {})
    for cid, c in confirmed.items():
        src = {"user_clarification": "user_clarification", "memory": "user_clarification",
               "assumed": "default"}.get(c.get("source"), "default")
        slots.append({"name": cid.replace("_", " "), "value": c["label"],
                      "status": "assumed" if c.get("source") == "assumed" else "confirmed", "source": src})
    if und.get("metric") and not any(s["name"] in ("metric",) for s in slots):
        slots.append({"name": "metric", "value": und["metric"], "status": "inferred", "source": "user_text"})
    if und.get("time_period"):
        slots.append({"name": "time period", "value": und["time_period"], "status": "inferred", "source": "user_text"})
    if und.get("limit"):
        slots.append({"name": "limit", "value": und["limit"], "status": "inferred", "source": "user_text"})
    return slots
