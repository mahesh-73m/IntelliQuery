import { useState } from "react";
import { Link } from "react-router-dom";
import { Bookmark, ChevronDown, ChevronRight, History as HistoryIcon, Trash2 } from "lucide-react";
import { useToast } from "../components/ui/Toast.jsx";
import { Badge, Empty, ErrorNote, Spinner } from "../components/ui/index.jsx";
import useAsync from "../hooks/useAsync";
import { errMsg, queries } from "../services/api";
import { fmtMs, timeAgo } from "../utils/format";

export default function History() {
  const [status, setStatus] = useState("");
  const [open, setOpen] = useState(null);
  const toast = useToast();
  const h = useAsync(() => queries.history(status ? { status, limit: 100 } : { limit: 100 }), [status]);
  const s = useAsync(queries.saved);

  const del = async (id) => { try { await queries.removeSaved(id); s.reload(); } catch (e) { toast(errMsg(e)); } };

  return (
    <div className="mx-auto max-w-6xl space-y-10 p-5 md:p-8">
      <section>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h1 className="text-2xl font-semibold">Query history</h1>
          <div className="flex gap-1" role="group" aria-label="Filter by status">
            {[["", "All"], ["success", "Successful"], ["error", "Failed"]].map(([v, l]) => (
              <button key={v} onClick={() => setStatus(v)} aria-pressed={status === v} className={`btn !py-1.5 ${status === v ? "btn-primary" : "btn-ghost"}`}>{l}</button>
            ))}
          </div>
        </div>
        <div className="mt-4">
          {h.loading && <Spinner />}
          {h.error && <ErrorNote>{h.error}</ErrorNote>}
          {h.data && h.data.length === 0 && <Empty icon={HistoryIcon} title="No queries here yet">Questions you run in the workspace are listed with their SQL, status and timing.</Empty>}
          {h.data?.length > 0 && (
            <div className="panel divide-y divide-line">
              {h.data.map((q) => (
                <div key={q.id}>
                  <button className="flex w-full items-center gap-3 px-4 py-3 text-left" onClick={() => setOpen(open === q.id ? null : q.id)} aria-expanded={open === q.id}>
                    {open === q.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    <span className="min-w-0 flex-1 truncate">{q.question}</span>
                    {q.was_clarified && <Badge tone="signal">clarified</Badge>}
                    <Badge tone={q.status === "success" ? "ok" : "bad"}>{q.status === "success" ? "success" : "failed"}</Badge>
                    <span className="hidden w-20 text-right text-xs text-muted sm:block">{fmtMs(q.execution_time_ms)}</span>
                    <span className="hidden w-20 text-right text-xs text-muted md:block">{timeAgo(q.created_at)}</span>
                  </button>
                  {open === q.id && (
                    <div className="space-y-2 bg-bg/60 px-4 pb-4 pl-11 text-sm">
                      {q.sql && <pre className="overflow-x-auto rounded-lg border border-line bg-surface p-3 font-mono text-xs">{q.sql}</pre>}
                      {q.error && <p className="text-bad">{q.error}</p>}
                      <p className="text-xs text-muted">{q.row_count ?? 0} rows · {q.attempts} attempt{q.attempts === 1 ? "" : "s"}
                        {q.conversation_id && <> · <Link className="text-accent underline" to={`/app/workspace?c=${q.conversation_id}`}>Continue this conversation</Link></>}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold">Saved queries</h2>
        <div className="mt-4">
          {s.data?.length === 0 && <Empty icon={Bookmark} title="No saved queries">Use “Save” on a result in the workspace to keep its SQL here.</Empty>}
          {s.data?.length > 0 && (
            <div className="grid gap-3 md:grid-cols-2">
              {s.data.map((x) => (
                <div key={x.id} className="panel p-4">
                  <div className="flex items-start justify-between gap-2"><p className="font-medium">{x.name}</p>
                    <button onClick={() => del(x.id)} aria-label={`Delete ${x.name}`} className="text-muted hover:text-bad"><Trash2 size={15} /></button></div>
                  <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-bg p-3 font-mono text-xs">{x.sql}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
