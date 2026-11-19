"""Builds tests/eval/dataset.jsonl (100 questions) with gold SQL.  Run: python tests/eval/build_dataset.py

Item fields
  category     : clear | ambiguous | incomplete | complex | multi_table
  expect_clarification : whether a good system should ask
  gold_sql     : for non-ambiguous items
  term_id/intended_option/interpretations : for ambiguous/incomplete items; interpretations maps
                 option_id -> gold SQL; `intended_option` is what the simulated user answers.
Gold SQL uses the same business conventions as app/ai/semantic/metrics.yaml.
"""
import json
from pathlib import Path

REV = "SUM(oi.quantity * oi.unit_price)"
OK = "o.status IN ('completed','shipped')"
T = {  # phrase -> predicate on a date column
    "last month": lambda c: f"{c} >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month' AND {c} < date_trunc('month', CURRENT_DATE)",
    "this month": lambda c: f"{c} >= date_trunc('month', CURRENT_DATE)",
    "this year": lambda c: f"{c} >= date_trunc('year', CURRENT_DATE)",
    "in the last 30 days": lambda c: f"{c} >= CURRENT_DATE - INTERVAL '30 days'",
    "in the last 90 days": lambda c: f"{c} >= CURRENT_DATE - INTERVAL '90 days'",
}
items = []


def add(category, question, **kw):
    items.append({"id": f"Q{len(items) + 1:03d}", "category": category, "question": question, **kw})


def clear(q, sql):
    add("clear", q, expect_clarification=False, gold_sql=sql)


# ------------------------------------------------------------------ CLEAR (32)
for p in ("last month", "this month", "this year", "in the last 30 days"):
    clear(f"How many orders were placed {p}?", f"SELECT COUNT(*) AS order_count FROM orders o WHERE {T[p]('o.order_date')}")
for p in ("last month", "this year", "in the last 30 days"):
    clear(f"What was the total revenue {p}?",
          f"SELECT {REV} AS total_revenue FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE {OK} AND {T[p]('o.order_date')}")
for p in ("last month", "in the last 90 days", "this year"):
    clear(f"Show the top 5 customers by revenue {p}",
          f"SELECT c.name, {REV} AS total_revenue FROM customers c JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id "
          f"WHERE {OK} AND {T[p]('o.order_date')} GROUP BY c.id, c.name ORDER BY total_revenue DESC LIMIT 5")
for p in ("last month", "in the last 90 days", "this year"):
    clear(f"List the top 10 products by units sold {p}",
          f"SELECT p.name, SUM(oi.quantity) AS units_sold FROM products p JOIN order_items oi ON oi.product_id = p.id JOIN orders o ON o.id = oi.order_id "
          f"WHERE {OK} AND {T[p]('o.order_date')} GROUP BY p.id, p.name ORDER BY units_sold DESC LIMIT 10")
clear("How many orders are there in each status?", "SELECT status, COUNT(*) AS order_count FROM orders GROUP BY status")
clear("How many customers do we have in each country?", "SELECT country, COUNT(*) AS customer_count FROM customers GROUP BY country")
clear("How many products are in each category?",
      "SELECT c.name, COUNT(p.id) AS product_count FROM categories c LEFT JOIN products p ON p.category_id = c.id GROUP BY c.id, c.name")
clear("What is the average product price in each category?",
      "SELECT c.name, AVG(p.price) AS avg_price FROM categories c JOIN products p ON p.category_id = c.id GROUP BY c.id, c.name")
clear("Which product is the most expensive?", "SELECT name, price FROM products ORDER BY price DESC LIMIT 1")
clear("List the products that are out of stock", "SELECT name, stock FROM products WHERE stock = 0")
clear("How many customers have never placed an order?",
      "SELECT COUNT(*) AS customer_count FROM customers c WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)")
for p in ("last month", "this year", "in the last 90 days"):
    clear(f"What is the average order value {p}?",
          f"SELECT AVG(o.total_amount) AS avg_order_value FROM orders o WHERE {OK} AND {T[p]('o.order_date')}")
for p in ("last month", "this year", "in the last 90 days"):
    clear(f"How many cancelled orders were there {p}?",
          f"SELECT COUNT(*) AS cancelled_orders FROM orders o WHERE o.status = 'cancelled' AND {T[p]('o.order_date')}")
for p in ("last month", "this year", "in the last 90 days"):
    clear(f"Show total revenue by product category {p}",
          f"SELECT cat.name, {REV} AS total_revenue FROM orders o JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id "
          f"JOIN categories cat ON cat.id = p.category_id WHERE {OK} AND {T[p]('o.order_date')} GROUP BY cat.id, cat.name")
for p in ("last month", "this year", "in the last 90 days"):
    clear(f"How many new customers joined {p}?",
          f"SELECT COUNT(*) AS new_customers FROM customers c WHERE {T[p]('c.created_at')}")

# ------------------------------------------------------------------ AMBIGUOUS (24)
CUST = {
    "revenue": lambda p: f"SELECT c.name, {REV} AS total_revenue FROM customers c JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id WHERE {OK} AND {p} GROUP BY c.id, c.name ORDER BY total_revenue DESC LIMIT 10",
    "order_count": lambda p: f"SELECT c.name, COUNT(DISTINCT o.id) AS order_count FROM customers c JOIN orders o ON o.customer_id = c.id WHERE {p} GROUP BY c.id, c.name ORDER BY order_count DESC LIMIT 10",
    "purchase_days": lambda p: f"SELECT c.name, COUNT(DISTINCT o.order_date) AS purchase_days FROM customers c JOIN orders o ON o.customer_id = c.id WHERE {p} GROUP BY c.id, c.name ORDER BY purchase_days DESC LIMIT 10",
}
PROD = {
    "quantity": lambda p: f"SELECT pr.name, SUM(oi.quantity) AS units_sold FROM products pr JOIN order_items oi ON oi.product_id = pr.id JOIN orders o ON o.id = oi.order_id WHERE {OK} AND {p} GROUP BY pr.id, pr.name ORDER BY units_sold DESC LIMIT 10",
    "revenue": lambda p: f"SELECT pr.name, {REV} AS total_revenue FROM products pr JOIN order_items oi ON oi.product_id = pr.id JOIN orders o ON o.id = oi.order_id WHERE {OK} AND {p} GROUP BY pr.id, pr.name ORDER BY total_revenue DESC LIMIT 10",
    "order_count": lambda p: f"SELECT pr.name, COUNT(DISTINCT oi.order_id) AS order_count FROM products pr JOIN order_items oi ON oi.product_id = pr.id JOIN orders o ON o.id = oi.order_id WHERE {OK} AND {p} GROUP BY pr.id, pr.name ORDER BY order_count DESC LIMIT 10",
}
PROFIT = {
    "total_profit": lambda p: f"SELECT pr.name, SUM(oi.quantity * (oi.unit_price - pr.cost)) AS total_profit FROM products pr JOIN order_items oi ON oi.product_id = pr.id JOIN orders o ON o.id = oi.order_id WHERE {OK} AND {p} GROUP BY pr.id, pr.name ORDER BY total_profit DESC LIMIT 10",
    "margin": lambda p: f"SELECT pr.name, ROUND(100.0 * SUM(oi.quantity * (oi.unit_price - pr.cost)) / NULLIF(SUM(oi.quantity * oi.unit_price), 0), 2) AS margin_pct FROM products pr JOIN order_items oi ON oi.product_id = pr.id JOIN orders o ON o.id = oi.order_id WHERE {OK} AND {p} GROUP BY pr.id, pr.name ORDER BY margin_pct DESC LIMIT 10",
}
CATS = {
    "revenue": lambda p: f"SELECT cat.name, {REV} AS total_revenue FROM categories cat JOIN products pr ON pr.category_id = cat.id JOIN order_items oi ON oi.product_id = pr.id JOIN orders o ON o.id = oi.order_id WHERE {OK} AND {p} GROUP BY cat.id, cat.name ORDER BY total_revenue DESC",
    "quantity": lambda p: f"SELECT cat.name, SUM(oi.quantity) AS units_sold FROM categories cat JOIN products pr ON pr.category_id = cat.id JOIN order_items oi ON oi.product_id = pr.id JOIN orders o ON o.id = oi.order_id WHERE {OK} AND {p} GROUP BY cat.id, cat.name ORDER BY units_sold DESC",
}
BIG = {
    "top_n": lambda p: f"SELECT o.id, o.total_amount FROM orders o WHERE {p} ORDER BY o.total_amount DESC LIMIT 10",
    "above_average": lambda p: f"SELECT o.id, o.total_amount FROM orders o WHERE {p} AND o.total_amount > (SELECT AVG(total_amount) FROM orders) ORDER BY o.total_amount DESC",
}
ALL_P = ["last month", "in the last 90 days", "this year"]


def amb(term, templates, phrases, builder):
    opts = list(templates)
    for i, p in enumerate(ALL_P):
        pred = T[p]("o.order_date")
        intended = opts[i % len(opts)]
        q = builder(p)
        add("ambiguous", q, expect_clarification=True, term_id=term, intended_option=intended,
            interpretations={k: f(pred) for k, f in templates.items()})


amb("best_customers", CUST, ALL_P, lambda p: f"Who are our best customers {p}?")
amb("best_customers", CUST, ALL_P, lambda p: f"Show our top customers {p}")
amb("best_selling_products", PROD, ALL_P, lambda p: f"What are the best-selling products {p}?")
amb("best_selling_products", PROD, ALL_P, lambda p: f"Show me the most popular products {p}")
amb("profitable_products", PROFIT, ALL_P, lambda p: f"Which products were the most profitable {p}?")
amb("best_categories", CATS, ALL_P, lambda p: f"What are the top categories {p}?")
amb("big_orders", BIG, ALL_P, lambda p: f"Show me the biggest orders {p}")
# 7 groups x 3 = 21; three more with different wording
for i, p in enumerate(ALL_P):
    pred = T[p]("o.order_date")
    intended = list(PROD)[(i + 1) % 3]
    add("ambiguous", f"List the top products {p}", expect_clarification=True, term_id="best_selling_products",
        intended_option=intended, interpretations={k: f(pred) for k, f in PROD.items()})

# ------------------------------------------------------------------ INCOMPLETE (14)
REC = {
    "d7": lambda col: f"{col} >= CURRENT_DATE - INTERVAL '7 days'",
    "d30": lambda col: f"{col} >= CURRENT_DATE - INTERVAL '30 days'",
    "d90": lambda col: f"{col} >= CURRENT_DATE - INTERVAL '90 days'",
}
for q, sqlf, intended in [
    ("Show me recent orders", lambda c: f"SELECT o.id, o.order_date, o.total_amount FROM orders o WHERE {c('o.order_date')}", "d30"),
    ("How many recent orders do we have?", lambda c: f"SELECT COUNT(*) AS order_count FROM orders o WHERE {c('o.order_date')}", "d7"),
    ("What is the revenue from recent orders?", lambda c: f"SELECT {REV} AS total_revenue FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE {OK} AND {c('o.order_date')}", "d90"),
    ("Show recent signups", lambda c: f"SELECT cu.id, cu.name, cu.created_at FROM customers cu WHERE {c('cu.created_at')}", "d30"),
]:
    add("incomplete", q, expect_clarification=True, term_id="recent", intended_option=intended,
        interpretations={k: sqlf(f) for k, f in REC.items()})

ACT = {"d30": 30, "d90": 90, "d365": 365}
add("incomplete", "How many active customers do we have?", expect_clarification=True, term_id="active_customers", intended_option="d90",
    interpretations={k: f"SELECT COUNT(DISTINCT o.customer_id) AS active_customers FROM orders o WHERE o.order_date >= CURRENT_DATE - INTERVAL '{n} days'" for k, n in ACT.items()})
add("incomplete", "List our active customers", expect_clarification=True, term_id="active_customers", intended_option="d30",
    interpretations={k: f"SELECT DISTINCT c.id, c.name FROM customers c JOIN orders o ON o.customer_id = c.id WHERE o.order_date >= CURRENT_DATE - INTERVAL '{n} days'" for k, n in ACT.items()})

TR = {  # option -> (filter, grain)
    "d30": ("o.order_date >= CURRENT_DATE - INTERVAL '30 days'", "day"),
    "d90": ("o.order_date >= CURRENT_DATE - INTERVAL '90 days'", "week"),
    "m12": ("o.order_date >= date_trunc('month', CURRENT_DATE) - INTERVAL '11 months'", "month"),
    "all": ("TRUE", "month"),
}
rev_trend = lambda flt, g: f"SELECT date_trunc('{g}', o.order_date) AS period, {REV} AS total_revenue FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE {OK} AND {flt} GROUP BY 1 ORDER BY 1"
ord_trend = lambda flt, g: f"SELECT date_trunc('{g}', o.order_date) AS period, COUNT(*) AS order_count FROM orders o WHERE {flt} GROUP BY 1 ORDER BY 1"
for q, fn, intended in [
    ("Show me the revenue trend", rev_trend, "m12"), ("How is revenue trending?", rev_trend, "d30"),
    ("Plot revenue over time", rev_trend, "all"), ("Show the sales trend", rev_trend, "d90"),
    ("Show me the order trend", ord_trend, "d90"), ("How are orders trending over time?", ord_trend, "m12"),
    ("Show the weekly order volume", ord_trend, "d30"), ("Show monthly orders", ord_trend, "all"),
]:
    add("incomplete", q, expect_clarification=True, term_id="trend_period", intended_option=intended,
        interpretations={k: fn(*v) for k, v in TR.items()})

# ------------------------------------------------------------------ COMPLEX (15)
def cx(q, sql): add("complex", q, expect_clarification=False, gold_sql=sql)

cx("Show monthly revenue this year",
   f"SELECT date_trunc('month', o.order_date) AS month, {REV} AS total_revenue FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE {OK} AND o.order_date >= date_trunc('year', CURRENT_DATE) GROUP BY 1 ORDER BY 1")
cx("What is the total revenue per customer for customers in India?",
   f"SELECT c.name, {REV} AS total_revenue FROM customers c JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id WHERE {OK} AND c.country = 'India' GROUP BY c.id, c.name")
cx("Which customers have placed more than 5 orders?",
   "SELECT c.name, COUNT(*) AS order_count FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.id, c.name HAVING COUNT(*) > 5")
cx("List customers who bought products from more than 2 different categories",
   "SELECT c.name, COUNT(DISTINCT p.category_id) AS category_count FROM customers c JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id GROUP BY c.id, c.name HAVING COUNT(DISTINCT p.category_id) > 2")
cx("What percentage of all orders are cancelled?",
   "SELECT 100.0 * COUNT(*) FILTER (WHERE status = 'cancelled') / COUNT(*) AS cancelled_pct FROM orders")
cx("Which category has the highest total revenue?",
   f"SELECT cat.name, {REV} AS total_revenue FROM categories cat JOIN products p ON p.category_id = cat.id JOIN order_items oi ON oi.product_id = p.id JOIN orders o ON o.id = oi.order_id WHERE {OK} GROUP BY cat.id, cat.name ORDER BY total_revenue DESC LIMIT 1")
cx("For each customer country, what is the total revenue?",
   f"SELECT c.country, {REV} AS total_revenue FROM customers c JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id WHERE {OK} GROUP BY c.country")
cx("What is the average number of line items per order?",
   "SELECT AVG(cnt) AS avg_line_items FROM (SELECT COUNT(*) AS cnt FROM order_items GROUP BY order_id) t")
cx("Show customers whose total revenue is above the average total revenue per customer",
   f"WITH rev AS (SELECT c.id, c.name, {REV} AS total_revenue FROM customers c JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id WHERE {OK} GROUP BY c.id, c.name) SELECT name, total_revenue FROM rev WHERE total_revenue > (SELECT AVG(total_revenue) FROM rev)")
cx("List products that have never been ordered",
   "SELECT p.name FROM products p WHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.product_id = p.id)")
cx("What share of total revenue does each product category contribute, as a percentage?",
   f"SELECT cat.name, 100.0 * {REV} / SUM({REV}) OVER () AS revenue_pct FROM categories cat JOIN products p ON p.category_id = cat.id JOIN order_items oi ON oi.product_id = p.id JOIN orders o ON o.id = oi.order_id WHERE {OK} GROUP BY cat.id, cat.name")
cx("Show the top 3 products by revenue within each category",
   f"SELECT category, product, total_revenue FROM (SELECT cat.name AS category, p.name AS product, {REV} AS total_revenue, ROW_NUMBER() OVER (PARTITION BY cat.id ORDER BY {REV} DESC) AS rn FROM categories cat JOIN products p ON p.category_id = cat.id JOIN order_items oi ON oi.product_id = p.id JOIN orders o ON o.id = oi.order_id WHERE {OK} GROUP BY cat.id, cat.name, p.id, p.name) t WHERE rn <= 3")
cx("Which customer has the highest average order amount among customers with at least 3 completed orders?",
   "SELECT c.name, AVG(o.total_amount) AS avg_order_amount FROM customers c JOIN orders o ON o.customer_id = c.id WHERE o.status = 'completed' GROUP BY c.id, c.name HAVING COUNT(*) >= 3 ORDER BY avg_order_amount DESC LIMIT 1")
cx("How many orders contain more than one distinct product?",
   "SELECT COUNT(*) AS order_count FROM (SELECT order_id FROM order_items GROUP BY order_id HAVING COUNT(DISTINCT product_id) > 1) t")
cx("What is the total refunded amount by month this year?",
   "SELECT date_trunc('month', order_date) AS month, SUM(total_amount) AS refunded_amount FROM orders WHERE status = 'refunded' AND order_date >= date_trunc('year', CURRENT_DATE) GROUP BY 1 ORDER BY 1")

# ------------------------------------------------------------------ MULTI-TABLE (15)
def mt(q, sql): add("multi_table", q, expect_clarification=False, gold_sql=sql)

mt("For each category name, how many distinct customers bought from it?",
   "SELECT cat.name, COUNT(DISTINCT o.customer_id) AS customer_count FROM categories cat JOIN products p ON p.category_id = cat.id JOIN order_items oi ON oi.product_id = p.id JOIN orders o ON o.id = oi.order_id GROUP BY cat.id, cat.name")
mt("Show each customer's name with their number of orders, including customers with none",
   "SELECT c.name, COUNT(o.id) AS order_count FROM customers c LEFT JOIN orders o ON o.customer_id = c.id GROUP BY c.id, c.name")
mt("What is the total quantity sold per product category?",
   "SELECT cat.name, SUM(oi.quantity) AS total_quantity FROM categories cat JOIN products p ON p.category_id = cat.id JOIN order_items oi ON oi.product_id = p.id GROUP BY cat.id, cat.name")
mt("How many customers are in each city?", "SELECT city, COUNT(*) AS customer_count FROM customers GROUP BY city")
mt("List order id, customer name and total amount for orders over 500",
   "SELECT o.id, c.name, o.total_amount FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.total_amount > 500")
mt("Show product name and category name for all products priced above 100",
   "SELECT p.name, cat.name AS category FROM products p JOIN categories cat ON cat.id = p.category_id WHERE p.price > 100")
mt("How many distinct customers bought each product?",
   "SELECT p.name, COUNT(DISTINCT o.customer_id) AS customer_count FROM products p JOIN order_items oi ON oi.product_id = p.id JOIN orders o ON o.id = oi.order_id GROUP BY p.id, p.name")
mt("Show total units sold for each product in the Electronics category",
   "SELECT p.name, SUM(oi.quantity) AS units_sold FROM products p JOIN categories cat ON cat.id = p.category_id JOIN order_items oi ON oi.product_id = p.id WHERE cat.name = 'Electronics' GROUP BY p.id, p.name")
mt("List customers from Germany along with their number of orders",
   "SELECT c.name, COUNT(o.id) AS order_count FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE c.country = 'Germany' GROUP BY c.id, c.name")
mt("What is the average order amount per customer country?",
   "SELECT c.country, AVG(o.total_amount) AS avg_order_amount FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.country")
mt("How many order items are there per product category?",
   "SELECT cat.name, COUNT(oi.id) AS item_count FROM categories cat JOIN products p ON p.category_id = cat.id JOIN order_items oi ON oi.product_id = p.id GROUP BY cat.id, cat.name")
mt("Show the total quantity of each product ordered by customers from India",
   "SELECT p.name, SUM(oi.quantity) AS total_quantity FROM products p JOIN order_items oi ON oi.product_id = p.id JOIN orders o ON o.id = oi.order_id JOIN customers c ON c.id = o.customer_id WHERE c.country = 'India' GROUP BY p.id, p.name")
mt("Show each category with the price of its most expensive product",
   "SELECT cat.name, MAX(p.price) AS max_price FROM categories cat JOIN products p ON p.category_id = cat.id GROUP BY cat.id, cat.name")
mt("List each customer with the date of their first order",
   "SELECT c.name, MIN(o.order_date) AS first_order_date FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.id, c.name")
mt("Show the number of orders per customer country and order status",
   "SELECT c.country, o.status, COUNT(*) AS order_count FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.country, o.status")

out = Path(__file__).with_name("dataset.jsonl")
out.write_text("\n".join(json.dumps(i, ensure_ascii=False) for i in items) + "\n", encoding="utf-8")
from collections import Counter
print(len(items), "items", dict(Counter(i["category"] for i in items)), "->", out)
