# Final-year project report outline
1. Introduction: problem (SQL barrier, ambiguity), objectives, scope
2. Literature review: Text-to-SQL (Spider, BIRD), LLM SQL generation, ambiguity and clarification in NLIDBs, semantic layers
3. Requirements analysis: functional, non-functional, security
4. System design: architecture, state machine, semantic layer, database design (ER diagram), API design
5. Implementation: schema discovery, understanding, clarification policy, SQL generation, validation (AST), execution, frontend
6. Security analysis: threat model (prompt injection, destructive SQL, exfiltration, resource abuse) and mitigations
7. Evaluation: dataset construction, metrics, experimental setup (basic vs intelligent, simulated user, N runs), results (from `reports/`), error analysis, threats to validity
8. Testing: unit, integration (smoke test), security test cases
9. Conclusion and future work: learned preferences, larger schemas, query cost estimation, multi-database
References, Appendices (SQL schema, prompts, dataset sample)
