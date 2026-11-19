import { Loader2 } from "lucide-react";

export const Spinner = ({ label = "Loading" }) => (
  <div className="flex items-center gap-2 text-sm text-muted" role="status"><Loader2 size={16} className="animate-spin" />{label}</div>
);

export const Empty = ({ icon: Icon, title, children }) => (
  <div className="flex flex-col items-start gap-2 py-10">
    {Icon && <Icon size={22} className="text-muted" />}
    <p className="font-medium">{title}</p>
    {children && <div className="max-w-md text-sm text-muted">{children}</div>}
  </div>
);

export const ErrorNote = ({ children }) => (
  <p className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad" role="alert">{children}</p>
);

export const Stat = ({ label, value, hint }) => (
  <div className="py-1">
    <p className="text-sm text-muted">{label}</p>
    <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
    {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
  </div>
);

export const Badge = ({ tone = "muted", children }) => {
  const tones = { ok: "bg-ok/15 text-ok", bad: "bg-bad/15 text-bad", signal: "bg-signal/25 text-ink", muted: "bg-line/60 text-muted", accent: "bg-accent/15 text-accent" };
  return <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
};
