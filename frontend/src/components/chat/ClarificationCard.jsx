import { CircleHelp } from "lucide-react";

/** One clarification question with selectable interpretations. `active` = still waiting for an answer. */
export default function ClarificationCard({ payload, active, busy, onPick }) {
  return (
    <div className="rise panel border-signal/70 p-4" role="group" aria-label="Clarification needed">
      <div className="flex items-start gap-2">
        <CircleHelp size={18} className="mt-0.5 shrink-0 text-signal" />
        <div>
          <p className="font-medium">{payload.prompt}</p>
          <p className="mt-0.5 text-xs text-muted">
            {active ? "Pick the closest meaning and I'll run the query." : "Answered"}
            {payload.max_rounds > 1 && ` (question ${payload.round} of at most ${payload.max_rounds})`}
          </p>
        </div>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {payload.options.map((o, i) => (
          <button key={o.id} disabled={!active || busy} onClick={() => onPick(o.id)}
            className="rounded-lg border border-line bg-bg p-3 text-left text-sm transition-colors hover:border-accent hover:bg-accent/10 disabled:cursor-default disabled:opacity-60 disabled:hover:border-line disabled:hover:bg-bg">
            <span className="mr-2 font-mono text-xs text-muted">{i + 1}</span>{o.label}
          </button>
        ))}
      </div>
    </div>
  );
}
