import { useMemo, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BarChart3, LineChart as LineIcon, PieChart as PieIcon, AreaChart as AreaIcon } from "lucide-react";
import { fmtCell } from "../../utils/format";

const COLORS = ["#2f4bff", "#e8a33d", "#1f8a5b", "#c8402f", "#7a5cff", "#0e9aa7", "#b0629a", "#6b7a86"];
const ICONS = { bar: BarChart3, line: LineIcon, area: AreaIcon, pie: PieIcon };

export default function ChartPanel({ columns, rows, chart }) {
  const [kind, setKind] = useState(chart?.recommended);
  const data = useMemo(() => {
    if (!chart?.x) return [];
    const xi = columns.indexOf(chart.x);
    const ys = chart.y.map((y) => columns.indexOf(y));
    return rows.slice(0, 200).map((r) => {
      const o = { [chart.x]: typeof r[xi] === "string" && /T00:00:00/.test(r[xi]) ? r[xi].slice(0, 10) : r[xi] };
      chart.y.forEach((y, i) => { o[y] = r[ys[i]]; });
      return o;
    });
  }, [columns, rows, chart]);

  if (!chart || chart.recommended === "table" || !data.length) return null;
  const axis = { stroke: "rgb(var(--muted))", fontSize: 12 };
  const tip = { contentStyle: { background: "rgb(var(--surface))", border: "1px solid rgb(var(--line))", borderRadius: 8, fontSize: 12 }, formatter: (v) => fmtCell(v) };
  const common = { data, margin: { top: 8, right: 12, left: 0, bottom: 4 } };
  const grid = <CartesianGrid stroke="rgb(var(--line))" strokeDasharray="3 3" />;
  const xa = <XAxis dataKey={chart.x} {...axis} interval="preserveStartEnd" tickFormatter={(v) => String(v).length > 12 ? String(v).slice(0, 11) + "…" : v} />;
  const ya = <YAxis {...axis} width={56} tickFormatter={(v) => Number(v).toLocaleString()} />;

  return (
    <div>
      <div className="mb-2 flex items-center gap-1" role="group" aria-label="Chart type">
        {chart.options.map((k) => {
          const I = ICONS[k];
          return (
            <button key={k} onClick={() => setKind(k)} aria-pressed={kind === k}
              className={`btn !px-2.5 !py-1.5 ${kind === k ? "btn-primary" : "btn-ghost"}`}><I size={15} />{k}</button>
          );
        })}
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer>
          {kind === "pie" ? (
            <PieChart>
              <Pie data={data} dataKey={chart.y[0]} nameKey={chart.x} outerRadius="80%" innerRadius="45%" paddingAngle={2}>
                {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip {...tip} /><Legend />
            </PieChart>
          ) : kind === "line" ? (
            <LineChart {...common}>{grid}{xa}{ya}<Tooltip {...tip} />{chart.y.length > 1 && <Legend />}
              {chart.y.map((y, i) => <Line key={y} type="monotone" dataKey={y} stroke={COLORS[i]} strokeWidth={2} dot={data.length < 40} />)}</LineChart>
          ) : kind === "area" ? (
            <AreaChart {...common}>{grid}{xa}{ya}<Tooltip {...tip} />{chart.y.length > 1 && <Legend />}
              {chart.y.map((y, i) => <Area key={y} type="monotone" dataKey={y} stroke={COLORS[i]} fill={COLORS[i]} fillOpacity={0.18} strokeWidth={2} />)}</AreaChart>
          ) : (
            <BarChart {...common}>{grid}{xa}{ya}<Tooltip {...tip} />{chart.y.length > 1 && <Legend />}
              {chart.y.map((y, i) => <Bar key={y} dataKey={y} fill={COLORS[i]} radius={[4, 4, 0, 0]} />)}</BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
