from app.services.chart_advisor import advise


def test_time_series_gets_line():
    r = advise(["month", "revenue"], [["2026-01-01", 10], ["2026-02-01", 12], ["2026-03-01", 9]])
    assert r["recommended"] == "line" and r["x"] == "month" and r["y"] == ["revenue"]


def test_few_categories_get_pie_many_get_bar():
    small = advise(["status", "n"], [["a", 1], ["b", 2], ["c", 3]])
    big = advise(["name", "n"], [[str(i), i] for i in range(20)])
    assert small["recommended"] == "pie" and big["recommended"] == "bar"


def test_single_row_or_no_numbers_is_table():
    assert advise(["a", "b"], [[1, 2]])["recommended"] == "table"
    assert advise(["a", "b"], [["x", "y"], ["z", "w"]])["recommended"] == "table"
