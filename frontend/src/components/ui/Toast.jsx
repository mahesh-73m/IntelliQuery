import { createContext, useCallback, useContext, useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

const Ctx = createContext(() => {});
export const useToast = () => useContext(Ctx);

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const push = useCallback((message, kind = "error") => {
    const id = Math.random().toString(36).slice(2);
    setItems((x) => [...x, { id, message, kind }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 5000);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex max-w-sm flex-col gap-2" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className="rise panel flex items-start gap-2 p-3 text-sm shadow-lg">
            {t.kind === "error" ? <AlertTriangle size={16} className="mt-0.5 shrink-0 text-bad" /> : <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-ok" />}
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
