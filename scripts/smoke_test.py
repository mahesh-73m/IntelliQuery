"""End-to-end smoke test against a running stack:  python scripts/smoke_test.py [http://localhost:8000]
Part 1 needs no LLM key (clarification is rule-based). Part 2 needs a configured LLM key."""
import sys
import uuid

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000") + "/api"
c = httpx.Client(timeout=120)


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name, extra)
    if not cond:
        sys.exit(1)


check("health", c.get(f"{BASE}/health").json() == {"status": "ok"})
email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
r = c.post(f"{BASE}/auth/register", json={"email": email, "full_name": "Smoke", "password": "password123"})
check("register", r.status_code == 201)
h = {"Authorization": f"Bearer {r.json()['access_token']}"}
check("unauthenticated is rejected", c.get(f"{BASE}/conversations").status_code == 401)
check("db status", c.get(f"{BASE}/database/status", headers=h).json()["connected"] is True)
check("schema discovery", set(c.get(f"{BASE}/database/schema", headers=h).json()["tables"]) >=
      {"customers", "orders", "order_items", "products", "categories"})

conv = c.post(f"{BASE}/conversations", json={}, headers=h).json()
cid = conv["id"]
r = c.post(f"{BASE}/conversations/{cid}/messages", json={"content": "Show me last month's best customers"}, headers=h)
body = r.json()
check("ambiguous question asks for clarification (no SQL run)",
      r.status_code == 200 and body["status"] == "clarification_needed", str([o["label"] for o in body["message"]["payload"].get("options", [])]))

for sql in ["DROP TABLE orders", "SELECT * FROM app.users", "SELECT 1; DELETE FROM orders", "SELECT pg_sleep(9) FROM orders"]:
    r = c.post(f"{BASE}/query/execute", json={"sql": sql}, headers=h)
    check(f"blocked: {sql}", r.status_code == 422, r.json().get("detail", ""))
r = c.post(f"{BASE}/query/execute", json={"sql": "SELECT status, COUNT(*) AS n FROM orders GROUP BY status"}, headers=h)
check("safe SELECT executes", r.status_code == 200 and r.json()["row_count"] > 0, f"{r.json().get('row_count')} rows")

# Part 2: needs an LLM key
r = c.post(f"{BASE}/conversations/{cid}/clarifications", json={"option_id": "revenue"}, headers=h)
print("LLM part ->", r.status_code, r.json()["status"], r.json()["message"]["content"] if r.status_code == 200 else r.json())
if r.status_code == 200 and r.json()["status"] == "completed":
    p = r.json()["message"]["payload"]
    print("SQL:", p["sql"], "\nrows:", p["row_count"], "\nsummary:", p["summary"])
print("smoke test finished")
