import { useCallback, useEffect, useState } from "react";
import { errMsg } from "../services/api";

/** Runs an async loader on mount (and on demand); exposes data / loading / error / reload. */
export default function useAsync(fn, deps = []) {
  const [state, set] = useState({ data: null, loading: true, error: null });
  const run = useCallback(() => {
    set((s) => ({ ...s, loading: true, error: null }));
    return fn().then(
      (data) => set({ data, loading: false, error: null }),
      (e) => set({ data: null, loading: false, error: errMsg(e) })
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { run(); }, [run]);
  return { ...state, reload: run };
}
