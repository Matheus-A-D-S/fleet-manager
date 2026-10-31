import { createContext, useContext, useEffect, useState } from "react";
import api, { getTokens, setTokens } from "./api.js";

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getTokens()) {
      setLoading(false);
      return;
    }
    api
      .get("/auth/me/")
      .then((r) => setUser(r.data))
      .catch(() => setTokens(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login/", { email, password });
    setTokens({ access: data.access, refresh: data.refresh });
    setUser(data.user);
  };

  const logout = async () => {
    const t = getTokens();
    try {
      if (t?.refresh) await api.post("/auth/logout/", { refresh: t.refresh });
    } catch {
      /* token já inválido: segue o logout local */
    }
    setTokens(null);
    setUser(null);
  };

  const isManager = !!user && ["ADMIN", "MANAGER"].includes(user.role);
  const isAdmin = !!user && user.role === "ADMIN";
  return <AuthCtx.Provider value={{ user, loading, login, logout, isManager, isAdmin }}>{children}</AuthCtx.Provider>;
}
