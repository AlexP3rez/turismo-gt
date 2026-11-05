import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, clearSession, getToken } from "./api.js";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function storedUser() {
  try {
    return JSON.parse(localStorage.getItem("user"));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(storedUser);
  const [ready, setReady] = useState(false);

  const saveUser = useCallback((u) => {
    localStorage.setItem("user", JSON.stringify(u));
    setUser(u);
  }, []);

  // Si la API responde 401 (token vencido), se cierra la sesión
  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, []);

  // Al abrir la app, valida el token guardado
  useEffect(() => {
    if (!getToken()) {
      setUser(null);
      setReady(true);
      return;
    }
    api("/auth/me")
      .then(saveUser)
      .catch(() => {})
      .finally(() => setReady(true));
  }, [saveUser]);

  const login = async (email, password) => {
    const data = await api("/auth/login", { method: "POST", form: { username: email, password } });
    localStorage.setItem("token", data.access_token);
    saveUser(data.user);
  };

  const register = async (email, full_name, password) => {
    await api("/auth/register", { method: "POST", body: { email, full_name, password } });
    await login(email, password);
  };

  const logout = async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      /* aunque falle, la sesión se cierra en el navegador */
    }
    clearSession();
    setUser(null);
  };

  // Actualiza los tokens usados/disponibles que se muestran en la barra lateral
  const refreshUser = useCallback(async () => {
    try {
      saveUser(await api("/auth/me"));
    } catch {
      /* si es 401, api() ya cerró la sesión */
    }
  }, [saveUser]);

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}