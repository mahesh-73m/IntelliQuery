import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { BarChart3, History, LayoutDashboard, LogOut, Menu, MessageSquareText, Moon, Settings, Sun, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";

const NAV = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/workspace", label: "Query workspace", icon: MessageSquareText },
  { to: "/app/history", label: "History", icon: History },
  { to: "/app/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/app/settings", label: "Settings", icon: Settings },
];

export const Logo = () => (
  <span className="flex items-center gap-2 text-lg font-semibold tracking-tight">
    <span className="grid h-7 w-7 place-items-center rounded-md bg-accent font-mono text-sm text-on-accent">?</span>IntelliQuery
  </span>
);

export default function AppShell({ children }) {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const nav = useNavigate();

  const side = (
    <div className="flex h-full flex-col gap-6 p-4">
      <div className="flex items-center justify-between"><Logo />
        <button className="md:hidden" onClick={() => setOpen(false)} aria-label="Close menu"><X size={20} /></button></div>
      <nav className="flex flex-col gap-1" aria-label="Main">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)}
            className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${isActive ? "bg-accent/12 font-medium text-accent" : "text-muted hover:bg-line/50 hover:text-ink"}`}>
            <Icon size={18} />{label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto space-y-2 border-t border-line pt-4 text-sm">
        <p className="truncate font-medium">{user?.full_name}</p>
        <p className="truncate text-xs text-muted">{user?.email}</p>
        <div className="flex gap-2">
          <button className="btn btn-ghost flex-1 !px-2" onClick={toggle} aria-label="Toggle dark mode">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}{theme === "dark" ? "Light" : "Dark"}
          </button>
          <button className="btn btn-ghost flex-1 !px-2" onClick={() => { logout(); nav("/"); }}><LogOut size={16} />Log out</button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 border-r border-line bg-surface md:block">{side}</aside>
      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 bg-surface shadow-xl">{side}</aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3 md:hidden">
          <button onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={22} /></button><Logo />
        </header>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
