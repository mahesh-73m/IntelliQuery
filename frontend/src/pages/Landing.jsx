import { Link } from "react-router-dom";
import { ArrowRight, Database, GitBranch, Moon, ShieldCheck, Sun, Table2 } from "lucide-react";
import { Logo } from "../components/layout/AppShell.jsx";
import { useTheme } from "../context/ThemeContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";

const STACK = ["React", "Vite", "Tailwind", "Recharts", "FastAPI", "Pydantic", "SQLAlchemy", "SQLGlot", "PostgreSQL", "Gemini / Groq / OpenAI"];

const FEATURES = [
  { icon: GitBranch, title: "It asks when your question has more than one meaning", body: "“Best customers” can mean revenue, order count or purchase frequency. IntelliQuery asks one short question, remembers your answer, and never guesses silently." },
  { icon: ShieldCheck, title: "Generated SQL is never trusted", body: "Every query is parsed into an AST, limited to a single SELECT on approved tables, then run on a read-only database role with a timeout and a row cap." },
  { icon: Database, title: "Knows your schema, not a generic one", body: "Tables, keys and relationships are discovered automatically, and business terms like revenue come from a definitions file, so answers stay consistent." },
  { icon: Table2, title: "Answers you can check", body: "Each answer shows the SQL, the result table, a chart and a plain-English summary. Edit the SQL and run it again if you want to." },
];

function Demo() {
  return (
    <div className="panel overflow-hidden text-sm shadow-xl" aria-label="Example conversation">
      <div className="space-y-3 p-4">
        <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-accent px-3 py-2 text-on-accent">Show me last month’s best customers</div>
        <div className="rounded-xl border border-signal/70 p-3">
          <p className="font-medium">What do you mean by best customers?</p>
          <div className="mt-2 space-y-1.5">
            {["Highest revenue generated", "Placed the most orders", "Purchased most frequently"].map((o, i) => (
              <div key={o} className={`rounded-lg border px-3 py-2 ${i === 0 ? "border-accent bg-accent/10" : "border-line bg-bg"}`}>{o}</div>
            ))}
          </div>
        </div>
        <pre className="overflow-x-auto rounded-lg bg-bg p-3 font-mono text-xs leading-relaxed">{`SELECT c.name,
  SUM(oi.quantity * oi.unit_price) AS total_revenue
FROM customers c
JOIN orders o ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
WHERE o.status IN ('completed','shipped')
  AND o.order_date >= date_trunc('month', CURRENT_DATE)
      - INTERVAL '1 month'
  AND o.order_date < date_trunc('month', CURRENT_DATE)
GROUP BY c.id, c.name
ORDER BY total_revenue DESC LIMIT 10`}</pre>
      </div>
    </div>
  );
}

export default function Landing() {
  const { theme, toggle } = useTheme();
  const { user } = useAuth();
  const cta = user ? "/app" : "/register";
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <Logo />
        <nav className="flex items-center gap-2">
          <button className="btn btn-ghost !px-2.5" onClick={toggle} aria-label="Toggle dark mode">{theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}</button>
          {!user && <Link to="/login" className="btn btn-ghost">Log in</Link>}
          <Link to={cta} className="btn btn-primary">{user ? "Open app" : "Get started"}</Link>
        </nav>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-10 px-5 pb-16 pt-10 lg:grid-cols-[1.05fr_1fr] lg:pt-16">
        <div>
          <h1 className="text-4xl font-semibold leading-[1.05] sm:text-5xl lg:text-6xl">Ask your database a question. It asks back when it needs to.</h1>
          <p className="mt-5 max-w-xl text-lg text-muted">IntelliQuery turns plain-English questions into safe PostgreSQL. When a question is vague, it clarifies before running anything, so you get the number you meant.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to={cta} className="btn btn-primary !px-5 !py-3 text-base">Get started <ArrowRight size={18} /></Link>
            <a href="#how" className="btn btn-ghost !px-5 !py-3 text-base">See how it works</a>
          </div>
        </div>
        <Demo />
      </section>

      <section id="how" className="border-y border-line bg-surface">
        <div className="mx-auto max-w-6xl px-5 py-14">
          <h2 className="max-w-2xl text-3xl font-semibold">Built so the answer is right, not just fast</h2>
          <div className="mt-8 grid gap-x-12 gap-y-8 md:grid-cols-2">
            {FEATURES.map(({ icon: I, title, body }) => (
              <div key={title} className="flex gap-4">
                <I size={22} className="mt-1 shrink-0 text-accent" />
                <div><h3 className="text-lg font-semibold">{title}</h3><p className="mt-1.5 text-muted">{body}</p></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-12">
        <h2 className="text-xl font-semibold">Technology</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          {STACK.map((s) => <span key={s} className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm">{s}</span>)}
        </div>
        <p className="mt-10 text-sm text-muted">IntelliQuery is a final-year B.Tech project. The sample database is a small online store with customers, orders, products and categories.</p>
      </section>
    </div>
  );
}
