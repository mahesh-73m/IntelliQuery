import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { useToast } from "../components/ui/Toast.jsx";
import { Badge, ErrorNote, Spinner } from "../components/ui/index.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";
import useAsync from "../hooks/useAsync";
import { auth, database, errMsg } from "../services/api";

export default function Settings() {
  const toast = useToast();
  const { user, setUser } = useAuth();
  const { theme, toggle } = useTheme();
  const st = useAsync(auth.settings);
  const db = useAsync(database.status);
  const sc = useAsync(database.schema);
  const [name, setName] = useState(user?.full_name || "");
  const [provider, setProvider] = useState("");
  useEffect(() => { if (st.data) setProvider(st.data.provider || ""); }, [st.data]);

  const save = async (patch) => {
    try { const r = await auth.updateSettings(patch); setUser(r.user); st.reload(); toast("Settings saved.", "ok"); } catch (e) { toast(errMsg(e)); }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-10 p-5 md:p-8">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Profile</h2>
        <form className="flex max-w-md flex-col gap-3 sm:flex-row" onSubmit={(e) => { e.preventDefault(); save({ full_name: name }); }}>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} aria-label="Full name" required maxLength={120} />
          <button className="btn btn-primary" disabled={!name.trim() || name === user?.full_name}>Save name</button>
        </form>
        <p className="text-sm text-muted">{user?.email}</p>
        <button className="btn btn-ghost" onClick={toggle}>{theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}Switch to {theme === "dark" ? "light" : "dark"} mode</button>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">AI provider</h2>
        {st.loading && <Spinner />}
        {st.error && <ErrorNote>{st.error}</ErrorNote>}
        {st.data && (
          <>
            <div className="grid max-w-xl gap-2">
              {["gemini", "groq", "openai"].map((p) => {
                const ok = st.data.providers[p];
                return (
                  <label key={p} className={`panel flex items-center gap-3 p-3 ${ok ? "cursor-pointer" : "opacity-60"}`}>
                    <input type="radio" name="provider" disabled={!ok} checked={provider === p} onChange={() => setProvider(p)} />
                    <span className="flex-1 font-medium capitalize">{p}</span>
                    <Badge tone={ok ? "ok" : "muted"}>{ok ? "key configured" : "no key on server"}</Badge>
                  </label>
                );
              })}
            </div>
            <button className="btn btn-primary" disabled={!provider || provider === st.data.provider} onClick={() => save({ provider })}>Use this provider</button>
            <p className="text-sm text-muted">API keys are set in the server’s <code className="font-mono">.env</code> file and are never sent to the browser. {!st.data.provider && "Until you choose, the server default is used."}</p>
          </>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Database connection</h2>
        {db.loading ? <Spinner /> : db.data && (
          <dl className="panel grid max-w-xl grid-cols-[8rem_1fr] gap-y-2 p-4 text-sm">
            <dt className="text-muted">Status</dt><dd>{db.data.connected ? <Badge tone="ok">connected</Badge> : <Badge tone="bad">unreachable</Badge>}</dd>
            <dt className="text-muted">Host</dt><dd>{db.data.host}</dd>
            <dt className="text-muted">Database</dt><dd>{db.data.database}</dd>
            <dt className="text-muted">Role</dt><dd>{db.data.role} (SELECT only)</dd>
            <dt className="text-muted">Latency</dt><dd>{db.data.latency_ms} ms</dd>
          </dl>
        )}
        <p className="text-sm text-muted">Connection details are configured on the server; credentials are never shown here.</p>
        {sc.data && (
          <details className="panel max-w-xl p-4 text-sm">
            <summary className="cursor-pointer font-medium">Discovered schema ({Object.keys(sc.data.tables).length} tables)</summary>
            <div className="mt-3 space-y-3">
              {Object.entries(sc.data.tables).map(([t, info]) => (
                <div key={t}><p className="font-mono font-medium">{t}</p>
                  <p className="font-mono text-xs text-muted">{info.columns.map((c) => `${c.name}${c.primary_key ? " (pk)" : ""}`).join(", ")}</p></div>
              ))}
            </div>
          </details>
        )}
      </section>
    </div>
  );
}
