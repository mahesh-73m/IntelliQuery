import pytest

pytest.importorskip("sqlglot")

from app.core.exceptions import SQLValidationError
from app.security.sql_validator import validate_sql

SCHEMA = {
    "customers": {"id", "name", "email", "city", "country", "created_at"},
    "orders": {"id", "customer_id", "order_date", "status", "total_amount"},
    "order_items": {"id", "order_id", "product_id", "quantity", "unit_price"},
    "products": {"id", "name", "category_id", "price", "cost", "stock"},
    "categories": {"id", "name"},
}
V = lambda sql, cap=1000: str(validate_sql(sql, SCHEMA, cap))

GOOD = [
    "SELECT COUNT(*) FROM orders WHERE order_date >= date_trunc('month', CURRENT_DATE)",
    "SELECT c.name, SUM(oi.quantity * oi.unit_price) AS total_revenue FROM customers c "
    "JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id "
    "WHERE o.status IN ('completed','shipped') GROUP BY c.id, c.name ORDER BY total_revenue DESC LIMIT 5",
    "WITH r AS (SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id) SELECT x.n FROM r x",
    "SELECT name FROM business.customers UNION SELECT name FROM products",
    "SELECT status, COUNT(*) FILTER (WHERE total_amount > 100) FROM orders GROUP BY status;",
]
BAD = [
    "DROP TABLE orders", "DELETE FROM orders", "UPDATE orders SET status='x'", "INSERT INTO orders VALUES (1)",
    "SELECT 1; DROP TABLE orders", "SELECT * FROM users", "SELECT * FROM app.users",
    "SELECT * FROM pg_catalog.pg_tables", "SELECT pg_sleep(10) FROM orders", "SELECT nonexistent FROM orders",
    "SELECT o.nope FROM orders o", "SELECT * INTO newt FROM orders", "SELECT * FROM orders FOR UPDATE",
    "SELECT 1", "", "SELECT * FROM generate_series(1, 10)", "SELECT current_setting('x') FROM orders",
    "COPY orders TO '/tmp/x'", "SELEC * FROM orders", "SELECT * FROM x.orders",
]


@pytest.mark.parametrize("sql", GOOD)
def test_valid_queries_pass(sql):
    assert V(sql).upper().startswith(("SELECT", "WITH"))


@pytest.mark.parametrize("sql", BAD)
def test_dangerous_or_invalid_queries_are_rejected(sql):
    with pytest.raises(SQLValidationError):
        V(sql)


def test_limit_is_enforced():
    assert "LIMIT 1000" in V("SELECT * FROM orders LIMIT 999999")
    assert "LIMIT 1000" in V("SELECT * FROM orders")
    assert "LIMIT 5" in V("SELECT * FROM orders LIMIT 5")
    assert "LIMIT 1000" in V("SELECT name FROM customers UNION SELECT name FROM products")
