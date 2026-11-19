import { fmtCell } from "../../utils/format";

export default function ResultsTable({ columns, rows, maxHeight = "20rem" }) {
  if (!rows.length) return <p className="px-1 py-4 text-sm text-muted">The query ran successfully but returned no rows.</p>;
  return (
    <div className="overflow-auto rounded-lg border border-line" style={{ maxHeight }}>
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0 bg-bg">
          <tr>{columns.map((c) => <th key={c} className="whitespace-nowrap border-b border-line px-3 py-2 text-left font-medium">{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="odd:bg-surface even:bg-bg/50">
              {r.map((v, j) => (
                <td key={j} className={`whitespace-nowrap px-3 py-1.5 ${typeof v === "number" ? "text-right tabular-nums" : ""} ${v === null ? "italic text-muted" : ""}`}>{fmtCell(v)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
