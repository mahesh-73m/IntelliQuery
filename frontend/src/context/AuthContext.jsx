import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { auth, TOKEN_KEY } from "../services/api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!localStorage.getItem(TOKEN_KEY));

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return;
    auth.me().then(setUser).catch(() => localStorage.removeItem(TOKEN_KEY)).finally(() => setReady(true));
  }, []);

  const finish = (data) => { localStorage.setItem(TOKEN_KEY, data.access_token); setUser(data.user); return data.user; };
  const login = useCallback((b) => auth.login(b).then(finish), []);
  const register = useCallback((b) => auth.register(b).then(finish), []);
  const logout = useCallback(() => { localStorage.removeItem(TOKEN_KEY); setUser(null); }, []);

  return <Ctx.Provider value={{ user, setUser, ready, login, register, logout }}>{children}</Ctx.Provider>;
}
