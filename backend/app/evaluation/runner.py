"""Benchmark runner.   python -m app.evaluation.runner --runs 1 --provider gemini

System A (basic):        question + schema -> LLM -> validate -> execute
System B (intelligent):  question -> clarification engine (+ simulated user) -> LLM -> validate -> execute
"""
import argparse
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.ai import pipeline
from app.ai.clarification import state_machine as sm
from app.ai.providers import get_provider
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.evaluation import simulated_user
from app.evaluation.metrics import aggregate, results_match
from app.evaluation.report import write_reports
from app.security.sql_validator import validate_sql
from app.services.query_executor import execute_select
from app.services.schema_inspector import get_schema
from app.services.schema_linker import link_schema

log = logging.getLogger("eval")
DATASET = Path(__file__).resolve().parent.parent.parent / "tests" / "eval" / "dataset.jsonl"
REPORT_DIR = Path(__file__).resolve().parent.parent.parent / "reports"


def load_dataset(categories: list[str] | None, limit: int | None) -> list[dict]:
    items = [json.loads(l) for l in DATASET.read_text(encoding="utf-8").splitlines() if l.strip()]
    if categories:
        items = [i for i in items if i["category"] in categories]
    if limit:
        per = max(1, -(-limit // len({i["category"] for i in items})))
        seen, picked = defaultdict(int), []
        for i in items:
            if seen[i["category"]] < per:
                picked.append(i)
                seen[i["category"]] += 1
        items = picked[:limit]
    return items


def gold_sql_for(item: dict) -> str:
    return item["gold_sql"] if "gold_sql" in item else item["interpretations"][item["intended_option"]]


def run_item(system: str, item: dict, provider, schema, gold_cache: dict) -> dict:
    rec = {"id": item["id"], "category": item["category"], "system": system,
           "expect_clarification": item["expect_clarification"], "asked": False, "rounds": 0, "executed": False,
           "correct": False, "exec_ms": None, "error": None, "sql": None, "answers_matched": True}
    q = item["question"]
    gold_sql = gold_sql_for(item)
    if gold_sql not in gold_cache:
        gold_cache[gold_sql] = execute_select(validate_sql(gold_sql, schema.column_map(), get_settings().max_result_rows))
    gold = gold_cache[gold_sql]
    schema_text = link_schema(q, schema)
    try:
        if system == "basic":
            gen = pipeline.basic_generate(provider, q, schema_text)
            rec["sql"] = gen.sql
            res = execute_select(validate_sql(gen.sql, schema.column_map(), get_settings().max_result_rows))
        else:
            state = sm.new_state(q)
            max_rounds = get_settings().max_clarification_rounds
            while True:
                d = sm.decide(state, max_rounds, lambda: pipeline.understand(provider, q, schema_text))
                if d.kind == "ask":
                    rec["asked"], rec["rounds"] = True, rec["rounds"] + 1
                    opt_id, matched = simulated_user.answer(item, d.candidate.id, [o["id"] for o in d.candidate.options])
                    rec["answers_matched"] &= matched
                    sm.apply_answer(state, opt_id)
                    continue
                break
            out = pipeline.generate_and_execute(provider, q, schema, schema_text, state["confirmed"])
            rec["sql"] = out.sql
            if out.result is None:
                raise AppError(out.error or "failed")
            res = out.result
        rec["executed"], rec["exec_ms"] = True, res.execution_time_ms
        rec["correct"] = results_match(gold, res, ordered="ORDER BY" in gold_sql.upper())
    except AppError as e:
        rec["error"] = e.message
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description="IntelliQuery benchmark")
    ap.add_argument("--systems", nargs="+", default=["basic", "intelligent"], choices=["basic", "intelligent"])
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--limit", type=int, default=None, help="evaluate a stratified subset of N questions")
    ap.add_argument("--categories", nargs="+", default=None)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--sleep", type=float, default=0.5, help="seconds between items (rate limits)")
    ap.add_argument("--no-save", action="store_true", help="do not write metrics to the database")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    provider = get_provider(args.provider)
    schema = get_schema()
    items = load_dataset(args.categories, args.limit)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    log.info("run %s: %d questions x %d system(s) x %d run(s) with %s", run_id, len(items), len(args.systems), args.runs, provider.name)

    gold_cache: dict = {}
    records: list[dict] = []
    for r in range(args.runs):
        for system in args.systems:
            for n, item in enumerate(items, 1):
                rec = run_item(system, item, provider, schema, gold_cache)
                rec["run"] = r + 1
                records.append(rec)
                log.info("[run %d] %-11s %s %-11s asked=%s executed=%s correct=%s", r + 1, system, item["id"],
                         item["category"], rec["asked"], rec["executed"], rec["correct"])
                time.sleep(args.sleep)

    summary = {}
    for system in args.systems:
        recs = [x for x in records if x["system"] == system]
        summary[system] = {"all": aggregate(recs)}
        for cat in sorted({x["category"] for x in recs}):
            summary[system][cat] = aggregate([x for x in recs if x["category"] == cat])
        summary[system]["all"]["per_run_accuracy"] = [
            aggregate([x for x in recs if x["run"] == r + 1])["execution_accuracy"] for r in range(args.runs)]

    REPORT_DIR.mkdir(exist_ok=True)
    paths = write_reports(run_id, provider.name, args.runs, summary, records, REPORT_DIR)
    if not args.no_save:
        _save(run_id, summary)
    log.info("reports written: %s", ", ".join(str(p) for p in paths))


def _save(run_id: str, summary: dict) -> None:
    from app.database.engines import SessionLocal
    from app.models.models import EvaluationMetric

    with SessionLocal() as db:
        for system, cats in summary.items():
            for cat, m in cats.items():
                for name, val in m.items():
                    if isinstance(val, (int, float)) and name != "n":
                        db.add(EvaluationMetric(run_id=run_id, system=system, category=cat, metric_name=name,
                                                value=float(val), details={"n": m["n"]}))
        db.commit()


if __name__ == "__main__":
    main()
