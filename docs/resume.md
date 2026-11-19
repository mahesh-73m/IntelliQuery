# Resume-ready description
**IntelliQuery: AI-Powered Text-to-SQL with Clarification Engine** (React, FastAPI, PostgreSQL, SQLGlot, Gemini)
- Built a full-stack natural-language database interface whose clarification engine (rule-based detector + LLM understanding + persisted state machine) asks one targeted question when a request is ambiguous, instead of guessing.
- Designed defense-in-depth SQL safety: SQLGlot AST validation with table/column/function allowlists, read-only Postgres role, statement timeouts and row caps.
- Created a YAML semantic layer for consistent business metrics; built a 100-question benchmark comparing basic vs clarification-first Text-to-SQL (execution accuracy, false/missed clarification rates).
- Delivered JWT auth, conversation memory, query history, auto-selected Recharts visualizations and Dockerized deployment.
(Add your measured benchmark numbers here after running the evaluation.)
