import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { FlaskConical } from "lucide-react";
import { Empty, ErrorNote, Spinner, Stat } from "../components/ui/index.jsx";
import useAsync from "../hooks/useAsync";
import { analytics } from "../services/api";
import { fmtMs, fmtNum, fmtPct } from "../utils/format";

const RATES = [
  ["execution_accuracy", "Execution accuracy"], ["successful_query_rate", "Successful query rate"],
  ["clarification_rate", "Clarification rate"], ["false_clarification_rate", "False clarification rate"],
  ["missed_ambiguity_rate", "Missed ambiguity rate"], ["clarification_resolution_rate", "Clarification resolution rate"],
];
const tip = { contentStyle: { background: "rgb(var(--surface))", border: "1px solid rgb(var(--line))", borderRadius: 8, fontSize: 12 }, formatter: (v) => `${v}%` };

export default function Analytics() {
  const ov = useAsync(analytics.overview);
  const ev = useAsync(analytics.evaluation);
  const o = ov.data;

  const pick = (system, category, metric) =>
    ev.data?.metrics.find((m) => m.system === system && m.category === category && m.metric === metric)?.value ?? null;
  const rows = ev.data?.run_id ? RATES.map(([k, label]) => ({
    metric: label, Basic: pick("basic", "all", k) == null ? null : +(pick("basic", "all", k) * 100).toFixed(1),
    Intelligent: pick("intelligent", "all", k) == null ? null : +(pick("intelligent", "all", k) * 100).toFixed(1),
  })) : [];
  const cats = [...new Set((ev.data?.metrics || []).map((m) => m.category).filter((c) => c !== "all"))];
  const byCat = cats.map((c) => ({
    category: c.replace("_", "-"),
    Basic: pick("basic", c, "execution_accuracy") == null ? null : +(pick("basic", c, "execution_accuracy") * 100).toFixed(1),
    Intelligent: pick("intelligent", c, "execution_accuracy") == null ? null : +(pick("intelligent", c, "execution_accuracy") * 100).toFixed(1),
  }));
  const raw = (s, k) => pick(s, "all", k);

  return (
    <div className="mx-auto max-w-6xl space-y-10 p-5 md:p-8">
      <h1 className="text-2xl font-semibold">Analytics and evaluation</h1>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Your usage</h2>
        {ov.loading && <Spinner />}
        {ov.error && <ErrorNote>{ov.error}</ErrorNote>}
        {o && (
          <div className="grid grid-cols-2 gap-x-8 gap-y-5 md:grid-cols-3 lg:grid-cols-5">
            <Stat label="Success rate" value={fmtPct(o.success_rate)} hint={`${fmtNum(o.successful_queries)} of ${fmtNum(o.total_queries)} queries`} />
            <Stat label="Failed queries" value={fmtNum(o.failed_queries)} />
            <Stat label="Clarifications asked" value={fmtNum(o.clarification_requests)} />
            <Stat label="Resolution rate" value={fmtPct(o.clarification_resolution_rate)} hint="questions you answered" />
            <Stat label="Avg execution time" value={fmtMs(o.avg_execution_ms)} />
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold">Benchmark: basic vs intelligent Text-to-SQL</h2>
        {ev.loading && <Spinner />}
        {ev.error && <ErrorNote>{ev.error}</ErrorNote>}
        {ev.data && !ev.data.run_id && (
          <Empty icon={FlaskConical} title="No benchmark has been run yet">
            Run it from the backend folder: <code className="rounded bg-line/60 px-1.5 py-0.5 font-mono text-xs">python -m app.evaluation.runner --runs 1</code>. Results from real executions appear here.
          </Empty>
        )}
        {ev.data?.run_id && (
          <div className="mt-4 space-y-8">
            <p className="text-sm text-muted">Run {ev.data.run_id}. Basic = question and schema straight to SQL. Intelligent = clarification engine first.</p>
            <div className="h-80">
              <ResponsiveContainer>
                <BarChart data={rows} margin={{ top: 8, right: 8, left: -8, bottom: 40 }}>
                  <CartesianGrid stroke="rgb(var(--line))" strokeDasharray="3 3" />
                  <XAxis dataKey="metric" stroke="rgb(var(--muted))" fontSize={11} interval={0} angle={-20} textAnchor="end" height={60} />
                  <YAxis domain={[0, 100]} stroke="rgb(var(--muted))" fontSize={12} unit="%" />
                  <Tooltip {...tip} /><Legend verticalAlign="top" />
                  <Bar dataKey="Basic" fill="#8a94a6" radius={[4, 4, 0, 0]} /><Bar dataKey="Intelligent" fill="#2f4bff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {byCat.length > 0 && (
              <div>
                <h3 className="mb-2 font-medium">Execution accuracy by question type</h3>
                <div className="h-64">
                  <ResponsiveContainer>
                    <BarChart data={byCat} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
                      <CartesianGrid stroke="rgb(var(--line))" strokeDasharray="3 3" />
                      <XAxis dataKey="category" stroke="rgb(var(--muted))" fontSize={12} />
                      <YAxis domain={[0, 100]} stroke="rgb(var(--muted))" fontSize={12} unit="%" />
                      <Tooltip {...tip} /><Legend />
                      <Bar dataKey="Basic" fill="#8a94a6" radius={[4, 4, 0, 0]} /><Bar dataKey="Intelligent" fill="#2f4bff" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            <div className="panel overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-bg"><tr><th className="px-4 py-2 text-left font-medium">Metric</th><th className="px-4 py-2 text-right font-medium">Basic</th><th className="px-4 py-2 text-right font-medium">Intelligent</th></tr></thead>
                <tbody>
                  {rows.map((r) => <tr key={r.metric} className="border-t border-line"><td className="px-4 py-2">{r.metric}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{r.Basic == null ? "n/a" : `${r.Basic}%`}</td><td className="px-4 py-2 text-right tabular-nums">{r.Intelligent == null ? "n/a" : `${r.Intelligent}%`}</td></tr>)}
                  <tr className="border-t border-line"><td className="px-4 py-2">Average execution time</td><td className="px-4 py-2 text-right tabular-nums">{fmtMs(raw("basic", "avg_execution_ms"))}</td><td className="px-4 py-2 text-right tabular-nums">{fmtMs(raw("intelligent", "avg_execution_ms"))}</td></tr>
                  <tr className="border-t border-line"><td className="px-4 py-2">Failed queries</td><td className="px-4 py-2 text-right tabular-nums">{fmtNum(raw("basic", "failed_count"))}</td><td className="px-4 py-2 text-right tabular-nums">{fmtNum(raw("intelligent", "failed_count"))}</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
