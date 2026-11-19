# Architecture

```
React (Vite, Tailwind, Recharts)  --REST+JWT-->  FastAPI
                                                   |
                                         Orchestrator (one turn)
   detect (rules) -> understand (LLM) -> policy/state machine -> [ask user | generate SQL]
   -> validate (SQLGlot AST) -> execute (read-only role) -> summarize + chart advice -> persist
                |                         |                         |
         Semantic layer           LLM providers               PostgreSQL
         metrics.yaml          Gemini / Groq / OpenAI     schema app (iq_app) | schema business (iq_readonly)
```
Key decisions: (1) the backend, not the browser, drives the state machine so SQL can never run before
ambiguities are resolved; (2) two DB roles and two schemas; (3) a semantic layer (`metrics.yaml`) defines
business terms and is the single source for both clarification options and SQL generation; (4) hybrid
ambiguity detection: deterministic rules decide most questions, the LLM only adds extra ones.

State machine: RECEIVED -> ANALYZING_AMBIGUITY -> AWAITING_USER <-> ANALYZING_AMBIGUITY -> READY_TO_GENERATE
-> GENERATING -> VALIDATING -> EXECUTING -> COMPLETED | FAILED (validation/DB errors are fed back to the LLM, max 2 retries).
