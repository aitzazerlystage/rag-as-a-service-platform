import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useEffect,
} from "react";

const STORAGE_KEY = "fileflow_auth";

/** @typedef {{ id: string, username: string, full_name: string, email: string }} User */
/** @typedef {{ id: string, name: string, plan_type?: string, max_users?: number } | null} Org */

const AuthContext = createContext(null);

function loadStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => loadStored()?.access_token ?? null);
  const [user, setUser] = useState(() => loadStored()?.user ?? null);
  const [organization, setOrganization] = useState(
    () => loadStored()?.organization ?? null
  );
  const [subscription, setSubscription] = useState(
    () => loadStored()?.subscription ?? null
  );

  useEffect(() => {
    if (!token || !user) {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        access_token: token,
        user,
        organization,
        subscription,
      })
    );
  }, [token, user, organization, subscription]);

  const setSession = useCallback((payload) => {
    setToken(payload.access_token ?? null);
    setUser(payload.user ?? null);
    setOrganization(payload.organization ?? null);
    setSubscription(payload.subscription ?? null);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setOrganization(null);
    setSubscription(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const value = useMemo(
    () => ({
      token,
      user,
      organization,
      subscription,
      isAuthenticated: Boolean(token && user),
      setSession,
      logout,
    }),
    [token, user, organization, subscription, setSession, logout]
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
