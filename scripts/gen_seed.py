"""Deterministically generates database/seed.sql (run: python scripts/gen_seed.py).

Dates are expressed relative to CURRENT_DATE through a helper function, so "last month"
always contains data no matter when the seed is loaded. The data is shaped so that the
three readings of "best customer" produce DIFFERENT rankings:
  * whales   : few orders, expensive electronics  -> top by revenue
  * frequent : many small orders, cheap items     -> top by order count / purchase days
  * bulk     : several orders on the same day     -> many orders, few purchase days
"""
import random
from pathlib import Path

rng = random.Random(42)
OUT = Path(__file__).resolve().parent.parent / "database" / "seed.sql"

CATEGORIES = ["Electronics", "Home & Kitchen", "Books", "Clothing", "Sports & Outdoors", "Beauty"]
PRODUCTS = {  # name: (category, price, cost)
    "Noise-Cancelling Headphones": (0, 199.99, 120), "4K Action Camera": (0, 249.00, 160),
    "Mechanical Keyboard": (0, 129.50, 70), "27-inch Monitor": (0, 329.00, 220),
    "Wireless Mouse": (0, 39.99, 18), "Portable SSD 1TB": (0, 119.00, 75),
    "Smart Speaker": (0, 79.99, 40), "Fitness Smartwatch": (0, 219.00, 130),
    "Air Fryer": (1, 89.99, 50), "Espresso Machine": (1, 259.00, 150),
    "Non-Stick Cookware Set": (1, 119.00, 60), "Robot Vacuum": (1, 299.00, 180),
    "Cotton Bedsheet Set": (1, 49.99, 22), "Electric Kettle": (1, 34.50, 16),
    "Python Crash Course": (2, 29.99, 12), "Data Science Handbook": (2, 44.00, 20),
    "Clean Architecture": (2, 36.50, 15), "Mystery Novel Collection": (2, 24.99, 9),
    "Cookbook: Everyday Indian": (2, 21.00, 8), "Children's Story Anthology": (2, 15.99, 6),
    "Denim Jacket": (3, 74.99, 32), "Running Shorts": (3, 24.99, 9),
    "Wool Sweater": (3, 64.00, 28), "Cotton T-Shirt Pack": (3, 27.99, 10),
    "Leather Belt": (3, 32.00, 12), "Rain Jacket": (3, 89.00, 40),
    "Yoga Mat": (4, 22.99, 8), "Camping Tent 4-Person": (4, 159.00, 90),
    "Trekking Backpack": (4, 94.99, 48), "Adjustable Dumbbell Set": (4, 139.00, 80),
    "Insulated Water Bottle": (4, 19.99, 7), "Cycling Helmet": (4, 54.00, 24),
    "Vitamin C Serum": (5, 18.99, 6), "Moisturising Cream": (5, 14.50, 5),
    "Herbal Shampoo": (5, 11.99, 4), "Sunscreen SPF 50": (5, 12.99, 4),
    "Hair Dryer": (5, 45.00, 20), "Face Mask Set": (5, 16.50, 6),
}
OUT_OF_STOCK = {"Robot Vacuum", "Cycling Helmet", "Hair Dryer"}

FIRST = ["Aarav","Vivaan","Ananya","Diya","Rohan","Ishita","Kabir","Meera","Arjun","Saanvi","Liam","Emma",
         "Noah","Olivia","Lucas","Mia","Ethan","Sophia","Hans","Greta","Felix","Lena","Oliver","Amelia",
         "Jack","Charlotte","Mateo","Camila","Yuki","Hana","Wei","Mei","Omar","Layla","Ravi","Priya"]
LAST = ["Sharma","Patel","Mishra","Das","Nair","Reddy","Smith","Johnson","Brown","Taylor","Müller","Schmidt",
        "Wagner","Becker","Wilson","Clark","Lopez","Garcia","Tanaka","Sato","Chen","Wang","Khan","Ali"]
PLACES = [("Bhubaneswar","India"),("Mumbai","India"),("Bengaluru","India"),("Delhi","India"),
          ("New York","USA"),("Austin","USA"),("Seattle","USA"),("London","UK"),("Manchester","UK"),
          ("Berlin","Germany"),("Munich","Germany"),("Toronto","Canada"),("Sydney","Australia")]

def q(s): return "'" + s.replace("'", "''") + "'"

names, seen = [], set()
while len(names) < 62:
    n = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    if n not in seen:
        seen.add(n); names.append(n)

customers = []
for i, n in enumerate(names, 1):
    city, country = PLACES[(i * 7) % len(PLACES)] if i > 12 else PLACES[i % 5]
    email = n.lower().replace(" ", ".").replace("ü", "u") + f"{i}@example.com"
    customers.append((i, n, email, city, country, (rng.randint(0, 5), rng.randint(0, 27))))

prod_list = list(PRODUCTS.items())
pid = {name: i for i, (name, _) in enumerate(prod_list, 1)}
by_cat = {c: [n for n, v in PRODUCTS.items() if v[0] == c] for c in range(6)}
expensive = [n for n in by_cat[0] if PRODUCTS[n][1] > 100]
cheap = by_cat[2] + by_cat[5] + [n for n in by_cat[4] + by_cat[3] if PRODUCTS[n][1] < 30]

orders = []   # (customer_id, month_offset, day, status, items[(product, qty, price)])

def status_for(m):
    r = rng.random()
    if m >= 2:
        return "completed" if r < 0.86 else ("cancelled" if r < 0.94 else "refunded")
    if m == 1:
        return "completed" if r < 0.70 else ("shipped" if r < 0.80 else ("cancelled" if r < 0.90 else ("refunded" if r < 0.95 else "pending")))
    return "shipped" if r < 0.40 else ("pending" if r < 0.65 else ("completed" if r < 0.85 else "cancelled"))

def make_items(pool, n_lines, qty_max=2, discount=0.0):
    items = []
    for name in rng.sample(pool, min(n_lines, len(pool))):
        price = PRODUCTS[name][1]
        if discount and rng.random() < 0.3:
            price = round(price * (1 - discount), 2)
        items.append((name, rng.randint(1, qty_max), price))
    return items

def add(cid, m, d, pool, lines, qty_max=2):
    if m == 0:
        d = min(d, 27)
    orders.append((cid, m, d, status_for(m), make_items(pool, lines, qty_max, 0.1)))

for cid in range(1, 7):                       # whales: 3-5 orders, big tickets, 2 in last month
    add(cid, 1, rng.randint(0, 27), expensive, 2); add(cid, 1, rng.randint(0, 27), expensive, 3)
    for _ in range(rng.randint(1, 3)):
        add(cid, rng.randint(2, 5), rng.randint(0, 27), expensive, rng.randint(1, 3))
for cid in range(7, 19):                      # frequent: 10-15 small orders spread over 6 months
    for m in range(0, 6):
        for _ in range(rng.randint(1, 3)):
            add(cid, m, rng.randint(0, 27), cheap, rng.randint(1, 2), 2)
for cid in range(19, 23):                     # bulk: several orders on the SAME days last month
    for day in (rng.randint(0, 13), rng.randint(14, 27)):
        for _ in range(3):
            add(cid, 1, day, cheap, 1, 3)
for cid in range(23, 56):                     # regular customers
    for _ in range(rng.randint(0, 6)):
        pool = rng.choice([cheap, expensive, [n for n in PRODUCTS]])
        add(cid, rng.randint(0, 5), rng.randint(0, 27), pool, rng.randint(1, 3))
# customers 56-62 intentionally never order

rng.shuffle(orders)

lines = ["-- GENERATED by scripts/gen_seed.py - do not edit by hand.", "BEGIN;",
         "CREATE FUNCTION pg_temp.mdate(m int, d int) RETURNS date LANGUAGE sql AS $$",
         "  SELECT CASE WHEN m = 0",
         "    THEN (date_trunc('month', CURRENT_DATE)::date + LEAST(d, EXTRACT(DAY FROM CURRENT_DATE)::int - 1))",
         "    ELSE ((date_trunc('month', CURRENT_DATE) - make_interval(months => m))::date + d) END $$;", ""]

lines.append("INSERT INTO business.categories (id, name) VALUES")
lines.append(",\n".join(f"  ({i}, {q(c)})" for i, c in enumerate(CATEGORIES, 1)) + ";\n")

lines.append("INSERT INTO business.products (id, name, category_id, price, cost, stock) VALUES")
rows = []
for name, (cat, price, cost) in prod_list:
    stock = 0 if name in OUT_OF_STOCK else rng.randint(5, 240)
    rows.append(f"  ({pid[name]}, {q(name)}, {cat + 1}, {price:.2f}, {cost:.2f}, {stock})")
lines.append(",\n".join(rows) + ";\n")

lines.append("INSERT INTO business.customers (id, name, email, city, country, created_at) VALUES")
lines.append(",\n".join(
    f"  ({i}, {q(n)}, {q(e)}, {q(c)}, {q(k)}, pg_temp.mdate({m + 0}, {d}) - {rng.randint(0, 45)})"
    for i, n, e, c, k, (m, d) in customers) + ";\n")

order_rows, item_rows = [], []
for oid, (cid, m, d, status, items) in enumerate(orders, 1):
    total = round(sum(qty * price for _, qty, price in items), 2)
    order_rows.append(f"  ({oid}, {cid}, pg_temp.mdate({m}, {d}), {q(status)}, {total:.2f})")
    for name, qty, price in items:
        item_rows.append(f"  ({oid}, {pid[name]}, {qty}, {price:.2f})")

lines.append("INSERT INTO business.orders (id, customer_id, order_date, status, total_amount) VALUES")
lines.append(",\n".join(order_rows) + ";\n")
lines.append("INSERT INTO business.order_items (order_id, product_id, quantity, unit_price) VALUES")
lines.append(",\n".join(item_rows) + ";\n")
for t in ("categories", "products", "customers", "orders"):
    lines.append(f"SELECT setval(pg_get_serial_sequence('business.{t}', 'id'), (SELECT MAX(id) FROM business.{t}));")
lines += ["COMMIT;", ""]
OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"customers={len(customers)} products={len(prod_list)} orders={len(orders)} items={len(item_rows)} -> {OUT}")
