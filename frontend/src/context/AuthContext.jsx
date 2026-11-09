import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authApi } from "../services/auth.js";

const AuthContext = createContext(null);

/**
 * Holds the current user for the whole app.
 *
 * status:
 *   "loading"         -> we are asking the server who is logged in
 *   "authenticated"   -> user is set
 *   "anonymous"       -> nobody is logged in
 *   "error"           -> the server could not be reached
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState("loading");

  const applySession = useCallback((session) => {
    setUser(session?.user ?? null);
    setStatus(session?.authenticated ? "authenticated" : "anonymous");
  }, []);

  const refresh = useCallback(async () => {
    setStatus("loading");
    try {
      applySession(await authApi.session());
    } catch {
      setUser(null);
      setStatus("error");
    }
  }, [applySession]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (email, password) => applySession(await authApi.login(email, password)),
    [applySession]
  );

  const register = useCallback(
    async (data) => applySession(await authApi.register(data)),
    [applySession]
  );

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
    setStatus("anonymous");
    // Django rotates the CSRF token on logout; fetch a fresh one.
    await authApi.session().catch(() => {});
  }, []);

  // After the settings page saved new profile data.
  const updateUser = useCallback((nextUser) => setUser(nextUser), []);

  const value = useMemo(
    () => ({ user, status, login, register, logout, refresh, updateUser }),
    [user, status, login, register, logout, refresh, updateUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
