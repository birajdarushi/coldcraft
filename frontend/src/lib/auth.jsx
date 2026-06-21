import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api.js";

const AuthContext = createContext({
  email: null,
  loading: true,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }) {
  const [email, setEmail] = useState(null);
  const [loading, setLoading] = useState(true);

  // Validate any stored token on first load.
  useEffect(() => {
    let alive = true;
    (async () => {
      if (!getToken()) {
        if (alive) setLoading(false);
        return;
      }
      try {
        const me = await api.me();
        if (alive) setEmail(me.email);
      } catch {
        setToken(""); // invalid/expired
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const login = (token, userEmail) => {
    setToken(token);
    setEmail(userEmail);
  };
  const logout = () => {
    setToken("");
    setEmail(null);
  };

  return (
    <AuthContext.Provider value={{ email, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
