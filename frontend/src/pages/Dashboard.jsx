import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight, CircleCheck, CircleX, Database, MessageSquareText } from "lucide-react";
import { Badge, Empty, ErrorNote, Spinner, Stat } from "../components/ui/index.jsx";
import useAsync from "../hooks/useAsync";
import { analytics, database } from "../services/api";
import { fmtMs, fmtNum, fmtPct, timeAgo } from "../utils/format";

export default function Dashboard() {
  const ov = useAsync(analytics.overview);
  const db = useAsync(database.status);
  const o = ov.data;
  return (
    <div className="mx-auto max-w-6xl space-y-8 p-5 md:p-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Link to="/app/workspace" className="btn btn-primary"><MessageSquareText size={16} />Ask a question</Link>
      </div>

      <div className="panel flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 text-sm">
        <span className="flex items-center gap-2 font-medium"><Database size={16} />Database</span>
        {db.loading ? <Spinner label="Checking" /> : db.data?.connected ? (
          <>
            <Badge tone="ok">connected</Badge>
            <span className="text-muted">{db.data.database} on {db.data.host} · {db.data.tables} tables · read-only role · {db.data.latency_ms} ms</span>
          </>
        ) : <Badge tone="bad">unreachable</Badge>}
      </div>

      {ov.loading && <Spinner />}
      {ov.error && <ErrorNote>{ov.error}</ErrorNote>}
      {o && (
        <>
          <div className="grid grid-cols-2 gap-x-8 gap-y-4 md:grid-cols-4">
            <Stat label="Queries executed" value={fmtNum(o.total_queries)} />
            <Stat label="Successful" value={fmtNum(o.successful_queries)} hint={o.success_rate != null ? `${fmtPct(o.success_rate)} success rate` : "No queries yet"} />
            <Stat label="Clarification requests" value={fmtNum(o.clarification_requests)} hint={o.clarification_resolution_rate != null ? `${fmtPct(o.clarification_resolution_rate)} answered` : undefined} />
            <Stat label="Average run time" value={fmtMs(o.avg_execution_ms)} />
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
            <section className="panel p-4">
              <h2 className="mb-3 font-semibold">Queries in the last 14 days</h2>
              {o.daily.length === 0 ? <Empty title="Nothing to chart yet">Ask your first question and activity will show up here.</Empty> : (
                <div className="h-60">
                  <ResponsiveContainer>
                    <AreaChart data={o.daily} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                      <CartesianGrid stroke="rgb(var(--line))" strokeDasharray="3 3" />
                      <XAxis dataKey="day" stroke="rgb(var(--muted))" fontSize={12} tickFormatter={(d) => d.slice(5)} />
                      <YAxis allowDecimals={false} stroke="rgb(var(--muted))" fontSize={12} />
                      <Tooltip contentStyle={{ background: "rgb(var(--surface))", border: "1px solid rgb(var(--line))", borderRadius: 8, fontSize: 12 }} />
                      <Area type="monotone" dataKey="total" name="Queries" stroke="#2f4bff" fill="#2f4bff" fillOpacity={0.15} strokeWidth={2} />
                      <Area type="monotone" dataKey="success" name="Successful" stroke="#1f8a5b" fill="#1f8a5b" fillOpacity={0.1} strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </section>

            <section className="panel p-4">
              <div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">Recent queries</h2>
                <Link to="/app/history" className="flex items-center gap-1 text-sm text-accent">All <ArrowRight size={14} /></Link></div>
              {o.recent.length === 0 ? <Empty title="No queries yet">Try “How many orders were placed last month?”</Empty> : (
                <ul className="divide-y divide-line">
                  {o.recent.map((r) => (
                    <li key={r.id} className="flex items-start gap-2 py-2.5 text-sm">
                      {r.status === "success" ? <CircleCheck size={16} className="mt-0.5 shrink-0 text-ok" /> : <CircleX size={16} className="mt-0.5 shrink-0 text-bad" />}
                      <span className="min-w-0 flex-1 truncate">{r.question}</span>
                      <span className="shrink-0 text-xs text-muted">{timeAgo(r.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
