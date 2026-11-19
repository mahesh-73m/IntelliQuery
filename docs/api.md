# API summary (full interactive docs at `/docs`)
All routes are under `/api`. Auth: `Authorization: Bearer <token>`.

| Method | Path | Purpose |
|---|---|---|
| POST | /auth/register, /auth/login | Create account / log in, returns token + user |
| GET | /auth/me, /auth/settings; PUT /auth/settings | Profile, AI provider preference |
| GET | /database/schema, /database/status | Discovered schema; connectivity (no credentials) |
| GET/POST | /conversations | List / create |
| GET/DELETE | /conversations/{id} | Messages + state / delete |
| POST | /conversations/{id}/messages `{content}` | Run one turn -> `clarification_needed` \| `completed` \| `error` |
| POST | /conversations/{id}/clarifications `{option_id}` | Answer the pending clarification and continue |
| POST | /query/execute `{sql, question?, conversation_id?}` | Run user-edited SQL (same validator) |
| GET | /query/history, /query/{id} | History |
| GET/POST/DELETE | /query/saved | Saved queries |
| GET | /analytics/overview, /analytics/evaluation | Usage metrics; latest benchmark run |
| POST | /debug/understand, /debug/clarify, /debug/generate-sql | Stage-by-stage (never executes SQL) |

Status codes: 401 unauthenticated, 404 not found / not yours, 409 invalid clarification state, 422 validation or SQL rejected,
429 rate limited, 502 LLM provider failure.
