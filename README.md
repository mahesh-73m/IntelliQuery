# IntelliQuery: AI-Powered Text-to-SQL with an Intelligent Clarification Engine

Ask a PostgreSQL database questions in plain English. When a question has more than one meaning
("best customers"), IntelliQuery asks **one** short clarification question before generating SQL, then
validates and runs the query safely and shows the SQL, a table, a chart and a plain-English summary.

**Stack:** React + Vite + Tailwind + Recharts | FastAPI + Pydantic + SQLAlchemy + SQLGlot | PostgreSQL | Gemini (Groq / OpenAI pluggable)

## Quick start (Docker, recommended)

```bash
cp .env.example .env
# edit .env: set SECRET_KEY, POSTGRES_PASSWORD, IQ_APP_PASSWORD, IQ_RO_PASSWORD and at least one LLM key (GEMINI_API_KEY)
docker compose up --build
```
- App: http://localhost:8080  |  API docs (Swagger): http://localhost:8000/docs
- The database is created, seeded (62 customers, 38 products, 287 orders) and the two DB roles are created on first start.
- To reset the database: `docker compose down -v` then `up` again.

Verify it works (no LLM key needed for the first part):
```bash
pip install httpx && python scripts/smoke_test.py http://localhost:8000
```

## Manual setup (no Docker)
```bash
# 1. Database (PostgreSQL 14+)
createdb intelliquery
export POSTGRES_USER=postgres POSTGRES_DB=intelliquery IQ_APP_PASSWORD=... IQ_RO_PASSWORD=...
bash database/00_roles.sh
psql -d intelliquery -f database/schema.sql
psql -d intelliquery -f database/seed.sql        # regenerate with: python scripts/gen_seed.py

# 2. Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env                        # set URLs, SECRET_KEY, an LLM key
uvicorn app.main:app --reload

# 3. Frontend (new terminal)
cd frontend && npm install && npm run dev         # http://localhost:5173 (proxies /api to :8000)
```

## How the clarification engine works
1. **Detect**: a rule-based detector checks the question against the semantic layer
   (`backend/app/ai/semantic/metrics.yaml`): vague terms (best, top, popular, profitable, recent, active,
   trend with no period...) that the user has not already made explicit.
2. **Understand**: the LLM produces a Pydantic-validated structure (intent, metric, period, limit,
   ambiguities). It may flag extra ambiguities, but at most one LLM-raised question per query.
3. **Policy** (`state_machine.py`): ask only if the term is ambiguous, not specified, has no safe default,
   was not answered earlier in the conversation, and the round cap (3) is not reached. One question at a time.
   After the cap it proceeds with the first option and reports the assumption.
4. **State** lives in `app.conversations.state` (JSONB), so conversations can be resumed and earlier answers are remembered.
5. Only when the state reaches `READY_TO_GENERATE` is SQL generated, validated and executed.

## Security model (defense in depth)
| Layer | Control |
|---|---|
| Database | `iq_readonly` role: SELECT on `business.*` only; read-only transactions; 5 s statement timeout; `search_path=business`. App tables (`app` schema) are invisible to it. |
| Validation | SQLGlot AST: exactly one statement; root must be SELECT/UNION; no INSERT/UPDATE/DELETE/DDL/COPY/INTO/FOR UPDATE; table and column allowlist from the live schema; function denylist (`pg_sleep`, `pg_read_file`, `dblink`, `set_config`, `lo_*`...); LIMIT forced to <= 1000. |
| Execution | Only a `ValidatedSQL` object can be executed; DB errors mapped to safe messages (no DSNs, stack traces). |
| App | bcrypt, short-lived JWT, per-user ownership checks (404 for others' data), rate limiting, CORS allowlist, secrets only via env. |
| Prompt injection | Result rows are never fed back into the SQL-generation prompt; the summarizer gets <= 10 rows and is told to treat them as data. |

Note on parameterization: LLM-generated literals are not extracted into bind parameters. Because the AST is
validated to a single read-only SELECT, a literal cannot change statement structure; this is a deliberate simplification.

## Evaluation (basic vs intelligent)
```bash
cd backend
python tests/eval/build_dataset.py                 # regenerates the 100-question dataset (already included)
python -m app.evaluation.runner --runs 1           # needs an LLM key; ~100 questions x 2 systems
python -m app.evaluation.runner --limit 20 --runs 1   # quick stratified subset
```
Writes `backend/reports/eval_<run>.{json,md,html}` and stores metrics in `app.evaluation_metrics`
(shown on the Analytics page). **No results are shipped with this repo; run it to get real numbers.**
Dataset: 32 clear, 24 ambiguous, 14 incomplete, 15 complex, 15 multi-table. Metrics: execution accuracy,
successful query rate, clarification rate, false clarification rate, missed ambiguity rate, clarification
resolution rate, average execution time, failed count. System B uses a simulated user that answers from the
dataset's ground truth. LLM output is non-deterministic: use `--runs 3` and report counts with percentages.

## Tests
```bash
cd backend && pytest tests/unit
```
Unit tests cover the detector, state machine, chart advisor, metrics and the SQL validator (incl. attack strings).

## API (see docs/api.md and /docs)
Auth, conversations (`POST /api/conversations/{id}/messages`, `.../clarifications`), `POST /api/query/execute`,
history, saved queries, database schema/status, analytics, and `/api/debug/*` (understand / clarify / generate-sql stages).

## Project layout
`backend/app/{api,core,database,models,schemas,security,services,ai,evaluation}`, `frontend/src/{components,pages,services,hooks,context,utils}`,
`database/{00_roles.sh,schema.sql,seed.sql}`, `docs/`, `scripts/`.

## Production checklist
Set `APP_ENV=production` and a real `SECRET_KEY`; use strong DB passwords; terminate TLS in front of nginx;
restrict `CORS_ORIGINS`; the in-memory rate limiter is per-process (use Redis for multiple workers).
