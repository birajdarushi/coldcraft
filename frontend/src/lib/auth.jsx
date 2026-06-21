import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api.js";

const GUEST_KEY = "coldcraft-guest";

const AuthContext = createContext({
  email: null,
  isGuest: false,
  loading: true,
  login: () => {},
  loginAsGuest: () => {},
  logout: () => {},
});

export function AuthProvider({ children }) {
  const [email, setEmail] = useState(null);
  const [isGuest, setIsGuest] = useState(false);
  const [loading, setLoading] = useState(true);

  // Restore a session (token) or guest mode on first load.
  useEffect(() => {
    let alive = true;
    (async () => {
      if (getToken()) {
        try {
          const me = await api.me();
          if (alive) setEmail(me.email);
        } catch {
          setToken(""); // invalid/expired
        } finally {
          if (alive) setLoading(false);
        }
        return;
      }
      if (localStorage.getItem(GUEST_KEY) === "1") {
        if (alive) {
          setEmail("Guest");
          setIsGuest(true);
        }
      }
      if (alive) setLoading(false);
    })();
    return () => {
      alive = false;
    };
  }, []);

  const login = (token, userEmail) => {
    localStorage.removeItem(GUEST_KEY);
    setIsGuest(false);
    setToken(token);
    setEmail(userEmail);
  };
  const loginAsGuest = () => {
    localStorage.setItem(GUEST_KEY, "1");
    setToken("");
    setIsGuest(true);
    setEmail("Guest");
  };
  const logout = () => {
    localStorage.removeItem(GUEST_KEY);
    setToken("");
    setIsGuest(false);
    setEmail(null);
  };

  return (
    <AuthContext.Provider value={{ email, isGuest, loading, login, loginAsGuest, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
