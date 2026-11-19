export const fmtMs = (v) => (v == null ? "-" : v < 1000 ? `${Math.round(v)} ms` : `${(v / 1000).toFixed(2)} s`);
export const fmtPct = (v) => (v == null ? "-" : `${Number(v).toFixed(1)}%`);
export const fmtNum = (v) => (v == null ? "-" : Number(v).toLocaleString());
export const fmtCell = (v) => {
  if (v === null || v === undefined) return "NULL";
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (typeof v === "boolean") return String(v);
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T00:00:00/.test(v)) return v.slice(0, 10);
  return String(v);
};
export const timeAgo = (iso) => {
  const s = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
};
export const EXAMPLES = [
  "How many orders were placed last month?",
  "Show me last month's best customers",
  "What are the best-selling products this year?",
  "Show me the revenue trend",
  "Which products were the most profitable in the last 90 days?",
  "How many customers do we have in each country?",
];
