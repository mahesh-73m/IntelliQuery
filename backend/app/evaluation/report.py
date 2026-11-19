"""Writes the evaluation report: JSON (raw), Markdown (tables) and a self-contained HTML page with SVG charts."""
import json
from pathlib import Path

METRICS = [
    ("execution_accuracy", "Execution accuracy", True),
    ("successful_query_rate", "Successful query rate", True),
    ("clarification_rate", "Clarification rate", True),
    ("false_clarification_rate", "False clarification rate", True),
    ("missed_ambiguity_rate", "Missed ambiguity rate", True),
    ("clarification_resolution_rate", "Clarification resolution rate", True),
    ("avg_execution_ms", "Avg execution time (ms)", False),
    ("failed_count", "Failed queries", False),
]


def _fmt(v, pct: bool) -> str:
    if v is None:
        return "n/a"
    return f"{v * 100:.1f}%" if pct else f"{v:g}"


def _table(summary: dict, scope: str) -> list[str]:
    systems = list(summary)
    rows = [f"| Metric | {' | '.join(systems)} |", "|---|" + "---|" * len(systems)]
    rows.append("| Questions (n) | " + " | ".join(str(summary[s][scope]["n"]) for s in systems) + " |")
    for key, label, pct in METRICS:
        rows.append(f"| {label} | " + " | ".join(_fmt(summary[s][scope].get(key), pct) for s in systems) + " |")
    return rows


def _svg_bars(title: str, series: dict[str, dict[str, float | None]]) -> str:
    """Grouped bar chart. series: system -> {label: value in [0,1]}."""
    labels = list(next(iter(series.values())).keys())
    colors = ["#8a94a6", "#2f4bff", "#e8a33d"]
    w, h, left, bottom = 760, 300, 40, 70
    group_w = (w - left - 10) / max(len(labels), 1)
    bar_w = min(34, (group_w - 14) / max(len(series), 1))
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{title}" style="max-width:100%;font:12px sans-serif">',
           f'<text x="{left}" y="16" font-weight="600">{title}</text>']
    for t in (0, .25, .5, .75, 1):
        y = h - bottom - t * (h - bottom - 30)
        out.append(f'<line x1="{left}" x2="{w}" y1="{y}" y2="{y}" stroke="#ddd"/><text x="{left - 6}" y="{y + 4}" text-anchor="end">{int(t * 100)}%</text>')
    for gi, lab in enumerate(labels):
        gx = left + gi * group_w + 7
        for si, (sname, vals) in enumerate(series.items()):
            v = vals.get(lab) or 0
            bh = v * (h - bottom - 30)
            x, y = gx + si * bar_w, h - bottom - bh
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 3:.1f}" height="{bh:.1f}" fill="{colors[si % 3]}"/>')
            out.append(f'<text x="{x + (bar_w - 3) / 2:.1f}" y="{y - 3:.1f}" text-anchor="middle" font-size="10">{v * 100:.0f}</text>')
        out.append(f'<text x="{gx + group_w / 2 - 7:.1f}" y="{h - bottom + 16}" text-anchor="middle">{lab}</text>')
    for si, sname in enumerate(series):
        out.append(f'<rect x="{left + si * 120}" y="{h - 22}" width="12" height="12" fill="{colors[si % 3]}"/><text x="{left + si * 120 + 18}" y="{h - 12}">{sname}</text>')
    out.append("</svg>")
    return "".join(out)


def write_reports(run_id: str, provider: str, runs: int, summary: dict, records: list[dict], out_dir: Path) -> list[Path]:
    cats = sorted({c for s in summary.values() for c in s if c != "all"})
    md = ["# IntelliQuery evaluation report", "",
          f"Run `{run_id}` | provider `{provider}` | {runs} run(s) | all numbers computed from real executions.", "",
          "## Overall", ""] + _table(summary, "all")
    for c in cats:
        md += ["", f"## Category: {c}", ""] + _table(summary, c)
    md += ["", "## Notes", "",
           "- Execution accuracy compares result sets to gold SQL (floats rounded to 2 dp, column order ignored).",
           "- Missed/false clarification rates are defined against the dataset's `expect_clarification` labels.",
           "- LLM output is non-deterministic: treat small differences with caution; see per-run accuracy in the JSON."]
    html = ["<!doctype html><meta charset=utf-8><title>IntelliQuery evaluation</title>",
            "<body style='font:15px system-ui;max-width:860px;margin:2rem auto;padding:0 1rem'>",
            f"<h1>IntelliQuery evaluation</h1><p>Run {run_id} · {provider} · {runs} run(s)</p>"]
    overall = {s: {lab: summary[s]["all"].get(k) for k, lab, pct in METRICS if pct and summary[s]["all"].get(k) is not None}
               for s in summary}
    shared = set.intersection(*(set(v) for v in overall.values())) if overall else set()
    overall = {s: {k: v for k, v in vals.items() if k in shared} for s, vals in overall.items()}
    if shared:
        html.append(_svg_bars("Overall rates", overall))
    by_cat = {s: {c: summary[s][c].get("execution_accuracy") for c in cats if c in summary[s]} for s in summary}
    html.append(_svg_bars("Execution accuracy by category", by_cat))
    html.append("<pre style='white-space:pre-wrap'>" + "\n".join(md) + "</pre></body>")
    out_dir.mkdir(exist_ok=True)
    paths = [out_dir / f"eval_{run_id}.json", out_dir / f"eval_{run_id}.md", out_dir / f"eval_{run_id}.html"]
    paths[0].write_text(json.dumps({"run_id": run_id, "provider": provider, "summary": summary, "records": records}, indent=2), encoding="utf-8")
    paths[1].write_text("\n".join(md), encoding="utf-8")
    paths[2].write_text("".join(html), encoding="utf-8")
    return paths
