import { useState } from "react";
import { Bookmark, Check, Clock, Copy, Play, Sparkles } from "lucide-react";
import { errMsg, queries } from "../../services/api";
import { fmtMs } from "../../utils/format";
import { useToast } from "../ui/Toast.jsx";
import { Badge, ErrorNote } from "../ui/index.jsx";
import ChartPanel from "../results/ChartPanel.jsx";
import ResultsTable from "../results/ResultsTable.jsx";

export default function ResultCard({ payload, conversationId }) {
  const toast = useToast();
  const [view, setView] = useState({ sql: payload.sql, columns: payload.columns, rows: payload.rows, row_count: payload.row_count,
    truncated: payload.truncated, ms: payload.execution_time_ms, chart: payload.chart, edited: !!payload.edited });
  const [sql, setSql] = useState(payload.sql);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [tab, setTab] = useState("table");
  const dirty = sql.trim() !== view.sql.trim();

  const run = async () => {
    setRunning(true); setError(null);
    try {
      const r = await queries.execute({ sql, question: payload.question, conversation_id: conversationId });
      setView({ sql: r.sql, columns: r.columns, rows: r.rows, row_count: r.row_count, truncated: r.truncated, ms: r.execution_time_ms, chart: r.chart, edited: true });
      setSql(r.sql);
    } catch (e) { setError(errMsg(e)); } finally { setRunning(false); }
  };
  const save = async () => {
    try { await queries.save({ name: payload.question.slice(0, 80), question: payload.question, sql: view.sql }); toast("Saved to your queries.", "ok"); }
    catch (e) { toast(errMsg(e)); }
  };
  const copy = () => { navigator.clipboard?.writeText(view.sql); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  const canChart = view.chart && view.chart.recommended !== "table";

  return (
    <div className="rise panel divide-y divide-line">
      <div className="space-y-3 p-4">
        <p className="flex items-start gap-2"><Sparkles size={16} className="mt-1 shrink-0 text-accent" /><span>{payload.summary}</span></p>
        {(payload.slots?.length > 0 || payload.assumptions?.length > 0) && (
          <div className="flex flex-wrap gap-1.5">
            {payload.slots?.map((s, i) => (
              <Badge key={i} tone={s.status === "confirmed" ? "accent" : s.status === "assumed" ? "signal" : "muted"}>{s.name}: {String(s.value)}</Badge>
            ))}
          </div>
        )}
        {payload.assumptions?.map((a, i) => <p key={i} className="text-xs text-muted">{a}</p>)}
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
          <span className="flex items-center gap-1"><Clock size={13} />{fmtMs(view.ms)}</span>
          <span>{view.row_count.toLocaleString()} row{view.row_count === 1 ? "" : "s"}{view.truncated ? " (capped)" : ""}</span>
          {payload.attempts > 1 && <span>fixed automatically after {payload.attempts - 1} retry</span>}
          {view.edited && <Badge tone="signal">edited SQL</Badge>}
        </div>
      </div>

      <div className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-medium">Generated SQL</p>
          <div className="flex gap-1.5">
            <button className="btn btn-ghost !px-2.5 !py-1.5" onClick={copy}>{copied ? <Check size={14} /> : <Copy size={14} />}Copy</button>
            <button className="btn btn-ghost !px-2.5 !py-1.5" onClick={save}><Bookmark size={14} />Save</button>
            <button className="btn btn-primary !px-2.5 !py-1.5" onClick={run} disabled={running || !dirty}><Play size={14} />{running ? "Running" : "Run edited SQL"}</button>
          </div>
        </div>
        <textarea value={sql} onChange={(e) => setSql(e.target.value)} spellCheck={false} aria-label="SQL editor"
          rows={Math.min(12, Math.max(3, sql.split("\n").length + 1))}
          className="w-full resize-y rounded-lg border border-line bg-bg p-3 font-mono text-[13px] leading-relaxed" />
        <p className="mt-1 text-xs text-muted">Edits run through the same validator: SELECT only, one statement, read-only.</p>
        {error && <div className="mt-2"><ErrorNote>{error}</ErrorNote></div>}
      </div>

      <div className="p-4">
        {canChart && (
          <div className="mb-3 flex gap-1" role="tablist">
            {["table", "chart"].map((t) => (
              <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
                className={`btn !py-1.5 ${tab === t ? "btn-primary" : "btn-ghost"}`}>{t === "table" ? "Table" : "Chart"}</button>
            ))}
          </div>
        )}
        {tab === "chart" && canChart ? <ChartPanel columns={view.columns} rows={view.rows} chart={view.chart} /> : <ResultsTable columns={view.columns} rows={view.rows} />}
      </div>
    </div>
  );
}
