import pytest

from app.ai.clarification import state_machine as sm
from app.core.exceptions import AppError


def test_ambiguous_question_asks_one_question_then_proceeds():
    st = sm.new_state("Show me last month's best customers")
    d = sm.decide(st, max_rounds=3)
    assert d.kind == "ask" and d.candidate.id == "best_customers" and st["phase"] == "AWAITING_USER"
    sm.apply_answer(st, "revenue")
    d2 = sm.decide(st, max_rounds=3)
    assert d2.kind == "ready" and st["phase"] == "READY_TO_GENERATE"
    assert st["confirmed"]["best_customers"]["option_id"] == "revenue"
    assert st["was_clarified"] is True


def test_clear_question_never_asks():
    st = sm.new_state("How many orders were placed last month?")
    assert sm.decide(st, 3, understand_fn=lambda: {"requires_clarification": False}).kind == "ready"


def test_invalid_option_and_wrong_phase_are_rejected():
    st = sm.new_state("Show me the best customers")
    with pytest.raises(AppError):
        sm.apply_answer(st, "revenue")  # nothing pending yet
    sm.decide(st, 3)
    with pytest.raises(AppError):
        sm.apply_answer(st, "not-an-option")


def test_round_cap_assumes_first_option_and_reports_it():
    st = sm.new_state("Show the best customers who joined recently")
    d = sm.decide(st, max_rounds=1)          # asks the first (priority) question
    assert d.kind == "ask"
    sm.apply_answer(st, d.candidate.options[0]["id"])
    d = sm.decide(st, max_rounds=1)          # cap reached: proceeds with an assumption
    assert d.kind == "ready" and st["assumptions"]


def test_memory_skips_repeated_question():
    first = sm.new_state("Show me the best customers")
    sm.decide(first, 3)
    sm.apply_answer(first, "order_count")
    second = sm.new_state("Show me the best customers this year", memory=first["confirmed"])
    assert sm.decide(second, 3).kind == "ready"


def test_llm_flagged_ambiguity_is_asked_once():
    und = {"requires_clarification": True, "ambiguities": [
        {"slot": "filter", "term": "premium", "question": "What is premium?", "options": ["Price > 100", "Top category"]}]}
    st = sm.new_state("List premium products")
    d = sm.decide(st, 3, understand_fn=lambda: und)
    assert d.kind == "ask" and d.candidate.source == "llm"
    sm.apply_answer(st, "opt1")
    assert sm.decide(st, 3, understand_fn=lambda: und).kind == "ready"


def test_illegal_transition_raises():
    st = {"phase": "COMPLETED"}
    with pytest.raises(AppError):
        sm.transition(st, "EXECUTING")
