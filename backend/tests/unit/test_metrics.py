from types import SimpleNamespace as NS

from app.evaluation.metrics import aggregate, results_match


def R(cols, rows):
    return NS(columns=cols, rows=rows, row_count=len(rows))


def test_match_ignores_order_names_and_float_noise():
    gold = R(["a", "b"], [["x", 1.0], ["y", 2.004]])
    assert results_match(gold, R(["p", "q"], [["y", 2.0], ["x", 1]]), ordered=False)
    assert not results_match(gold, R(["p", "q"], [["y", 2.0], ["x", 1]]), ordered=True)
    assert not results_match(gold, R(["p", "q"], [["y", 9.0], ["x", 1]]), ordered=False)


def test_aggregate_rates():
    recs = [dict(executed=True, asked=a, correct=c, exec_ms=4.0, expect_clarification=e)
            for a, c, e in [(False, True, False), (True, True, True), (False, False, True), (True, False, False)]]
    m = aggregate(recs)
    assert m["false_clarification_rate"] == 0.5 and m["missed_ambiguity_rate"] == 0.5
    assert m["clarification_resolution_rate"] == 0.5 and m["failed_count"] == 0
