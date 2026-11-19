import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Logo } from "../components/layout/AppShell.jsx";
import { ErrorNote } from "../components/ui/index.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { errMsg } from "../services/api";

function Shell({ title, sub, children, footer }) {
  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-sm">
        <Link to="/"><Logo /></Link>
        <h1 className="mt-8 text-2xl font-semibold">{title}</h1>
        <p className="mt-1 text-sm text-muted">{sub}</p>
        <div className="mt-6">{children}</div>
        <p className="mt-6 text-sm text-muted">{footer}</p>
      </div>
    </div>
  );
}

function Field({ label, ...p }) {
  return (
    <label className="block text-sm"><span className="mb-1 block font-medium">{label}</span><input className="input" {...p} /></label>
  );
}

function useSubmit(fn) {
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError(null);
    try { await fn(); nav("/app/workspace"); } catch (err) { setError(errMsg(err)); } finally { setBusy(false); }
  };
  return { busy, error, submit };
}

export function Login() {
  const { login } = useAuth();
  const [f, setF] = useState({ email: "", password: "" });
  const { busy, error, submit } = useSubmit(() => login(f));
  return (
    <Shell title="Log in" sub="Welcome back." footer={<>New here? <Link className="text-accent underline" to="/register">Create an account</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email" type="email" autoComplete="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        <Field label="Password" type="password" autoComplete="current-password" required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
        {error && <ErrorNote>{error}</ErrorNote>}
        <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Logging in" : "Log in"}</button>
      </form>
    </Shell>
  );
}

export function Register() {
  const { register } = useAuth();
  const [f, setF] = useState({ full_name: "", email: "", password: "" });
  const { busy, error, submit } = useSubmit(() => register(f));
  return (
    <Shell title="Create your account" sub="Start asking questions in minutes." footer={<>Already registered? <Link className="text-accent underline" to="/login">Log in</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Full name" autoComplete="name" required value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} />
        <Field label="Email" type="email" autoComplete="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        <Field label="Password (8+ characters)" type="password" autoComplete="new-password" minLength={8} maxLength={72} required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
        {error && <ErrorNote>{error}</ErrorNote>}
        <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Creating account" : "Create account"}</button>
      </form>
    </Shell>
  );
}
