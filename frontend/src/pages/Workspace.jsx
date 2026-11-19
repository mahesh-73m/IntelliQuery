import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { MessageSquarePlus, PanelLeft, SendHorizonal, Trash2, TriangleAlert } from "lucide-react";
import ClarificationCard from "../components/chat/ClarificationCard.jsx";
import ResultCard from "../components/chat/ResultCard.jsx";
import { useToast } from "../components/ui/Toast.jsx";
import { Spinner } from "../components/ui/index.jsx";
import { conversations as api, errMsg } from "../services/api";
import { EXAMPLES, timeAgo } from "../utils/format";

export default function Workspace() {
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const [list, setList] = useState([]);
  const [conv, setConv] = useState(null); // {id, awaiting_clarification, messages}
  const [pending, setPending] = useState(null); // optimistic user text
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [drawer, setDrawer] = useState(false);
  const endRef = useRef(null);
  const activeId = params.get("c") ? Number(params.get("c")) : null;

  const refreshList = useCallback(() => api.list().then(setList).catch((e) => toast(errMsg(e))), [toast]);
  const open = useCallback((id) => api.get(id).then(setConv).catch((e) => { toast(errMsg(e)); setParams({}); }), [toast, setParams]);

  useEffect(() => { refreshList(); }, [refreshList]);
  useEffect(() => { if (activeId) open(activeId); else setConv(null); }, [activeId, open]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [conv?.messages?.length, pending, busy]);

  const ensureConversation = async () => {
    if (activeId) return activeId;
    const c = await api.create(null);
    setParams({ c: c.id }, { replace: true });
    return c.id;
  };

  const turn = async (fn, optimistic) => {
    setBusy(true); setPending(optimistic || null);
    try {
      const id = await ensureConversation();
      await fn(id);
      await open(id);
      refreshList();
    } catch (e) {
      toast(errMsg(e));
      if (activeId) open(activeId);
    } finally { setBusy(false); setPending(null); }
  };

  const send = (text) => {
    const q = (text ?? input).trim();
    if (q.length < 2 || busy) return;
    setInput("");
    turn((id) => api.send(id, q), q);
  };
  const pick = (optionId) => turn((id) => api.clarify(id, optionId));
  const remove = async (id) => {
    try { await api.remove(id); if (activeId === id) setParams({}); refreshList(); } catch (e) { toast(errMsg(e)); }
  };

  const messages = conv?.messages || [];
  const lastIdx = messages.length - 1;

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="p-3">
        <button className="btn btn-ghost w-full" onClick={() => { setParams({}); setDrawer(false); }}><MessageSquarePlus size={16} />New conversation</button>
      </div>
      <ul className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
        {list.length === 0 && <li className="px-2 py-3 text-sm text-muted">Conversations you start will appear here.</li>}
        {list.map((c) => (
          <li key={c.id} className={`group flex items-center rounded-lg ${c.id === activeId ? "bg-accent/12" : "hover:bg-line/50"}`}>
            <button className="min-w-0 flex-1 px-2.5 py-2 text-left" onClick={() => { setParams({ c: c.id }); setDrawer(false); }}>
              <span className="block truncate text-sm">{c.title}</span>
              <span className="text-xs text-muted">{timeAgo(c.updated_at)}{c.awaiting_clarification && " · needs your answer"}</span>
            </button>
            <button className="mr-1 rounded p-1.5 text-muted opacity-0 hover:text-bad focus:opacity-100 group-hover:opacity-100" aria-label={`Delete ${c.title}`} onClick={() => remove(c.id)}><Trash2 size={14} /></button>
          </li>
        ))}
      </ul>
    </div>
  );

  return (
    <div className="flex h-[calc(100vh-57px)] md:h-screen">
      <aside className="hidden w-64 shrink-0 border-r border-line bg-surface lg:block">{sidebar}</aside>
      {drawer && (
        <div className="fixed inset-0 z-30 lg:hidden"><div className="absolute inset-0 bg-black/40" onClick={() => setDrawer(false)} />
          <aside className="absolute left-0 top-0 h-full w-72 bg-surface shadow-xl">{sidebar}</aside></div>
      )}

      <section className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-line px-4 py-2.5 lg:hidden">
          <button className="btn btn-ghost !px-2.5" onClick={() => setDrawer(true)} aria-label="Conversations"><PanelLeft size={16} /></button>
          <span className="truncate text-sm font-medium">{conv?.title || "New conversation"}</span>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl space-y-4 p-4 md:p-6">
            {messages.length === 0 && !pending && (
              <div className="py-10">
                <h1 className="text-2xl font-semibold">What would you like to know?</h1>
                <p className="mt-1 text-muted">Ask in plain English. If a question could mean more than one thing, I’ll ask first.</p>
                <div className="mt-5 flex flex-wrap gap-2">
                  {EXAMPLES.map((e) => <button key={e} className="rounded-full border border-line bg-surface px-3.5 py-1.5 text-sm hover:border-accent" onClick={() => send(e)}>{e}</button>)}
                </div>
              </div>
            )}

            {messages.map((m, i) => {
              const p = m.payload || {};
              if (m.role === "user") {
                return <div key={m.id} className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-accent px-4 py-2.5 text-on-accent">{m.content}</div>;
              }
              if (p.type === "clarification") {
                return <ClarificationCard key={m.id} payload={p} busy={busy} active={i === lastIdx && conv.awaiting_clarification} onPick={pick} />;
              }
              if (p.type === "result") return <ResultCard key={m.id} payload={p} conversationId={conv.id} />;
              return (
                <div key={m.id} className="rise panel flex items-start gap-2 border-bad/50 p-4 text-sm" role="alert">
                  <TriangleAlert size={18} className="mt-0.5 shrink-0 text-bad" />
                  <div><p>{m.content}</p>{p.sql && <pre className="mt-2 overflow-x-auto rounded bg-bg p-2 font-mono text-xs">{p.sql}</pre>}
                    <p className="mt-1 text-xs text-muted">Try rephrasing the question, or ask something more specific.</p></div>
                </div>
              );
            })}

            {pending && <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-accent px-4 py-2.5 text-on-accent">{pending}</div>}
            {busy && <div className="panel p-4"><Spinner label="Working on it: checking the question, writing and validating SQL" /></div>}
            <div ref={endRef} />
          </div>
        </div>

        <form className="border-t border-line bg-bg p-3 md:p-4" onSubmit={(e) => { e.preventDefault(); send(); }}>
          <div className="mx-auto flex max-w-4xl gap-2">
            <input className="input !py-2.5" value={input} onChange={(e) => setInput(e.target.value)} maxLength={1000}
              placeholder={conv?.awaiting_clarification ? "Choose an option above, or type a new question" : "Ask about customers, orders, products…"} aria-label="Your question" />
            <button className="btn btn-primary" disabled={busy || input.trim().length < 2} aria-label="Send"><SendHorizonal size={16} />Ask</button>
          </div>
        </form>
      </section>
    </div>
  );
}
