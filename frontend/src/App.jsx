import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";
import AppShell from "./components/layout/AppShell.jsx";
import { Spinner } from "./components/ui/index.jsx";
import Landing from "./pages/Landing.jsx";
import { Login, Register } from "./pages/Auth.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Workspace from "./pages/Workspace.jsx";
import History from "./pages/History.jsx";
import Analytics from "./pages/Analytics.jsx";
import Settings from "./pages/Settings.jsx";

function Protected() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="p-8"><Spinner /></div>;
  return user ? <AppShell><Outlet /></AppShell> : <Navigate to="/login" replace />;
}

function GuestOnly({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="p-8"><Spinner /></div>;
  return user ? <Navigate to="/app" replace /> : children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
      <Route path="/app" element={<Protected />}>
        <Route index element={<Dashboard />} />
        <Route path="workspace" element={<Workspace />} />
        <Route path="history" element={<History />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
