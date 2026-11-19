import pytest

from app.ai.clarification.detector import detect

AMBIGUOUS = {
    "Show me last month's best customers": "best_customers",
    "Show me the best-selling products.": "best_selling_products",
    "Which products were the most profitable last month?": "profitable_products",
    "Show me recent orders": "recent",
    "Show me the revenue trend": "trend_period",
    "How many active customers do we have?": "active_customers",
    "What are the top categories this year?": "best_categories",
    "Show the biggest orders this year": "big_orders",
}
CLEAR = [
    "How many orders were placed last month?",
    "Show the top 5 customers by revenue last month",
    "Top 10 products by units sold in the last 90 days",
    "Show monthly revenue for the last 6 months",
    "List orders over 500 dollars",
    "Show the 5 most recent orders",
    "Show best customers who placed the most orders",
]


@pytest.mark.parametrize("q,term", AMBIGUOUS.items())
def test_ambiguous_questions_are_detected(q, term):
    assert [c.id for c in detect(q)][:1] == [term]


@pytest.mark.parametrize("q", CLEAR)
def test_clear_questions_are_not_flagged(q):
    assert detect(q) == []


def test_options_have_ids_labels_and_instructions():
    for c in detect("Show me the best-selling products"):
        assert len(c.options) >= 2
        assert all({"id", "label", "instruction"} <= set(o) for o in c.options)
