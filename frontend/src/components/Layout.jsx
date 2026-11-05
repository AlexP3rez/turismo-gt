import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { API_BASE, api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { fmtNum } from "../utils.js";

const ROUTES = { rag_chat: "/chat", itinerary_planner: "/itinerary", plan_adjuster: "/adjust" };

export default function Layout() {
  const { user, logout, refreshUser } = useAuth();
  const [services, setServices] = useState([]);
  const { pathname } = useLocation();

  // Al cambiar de página se actualiza el menú de servicios (el admin puede activarlos o desactivarlos)
  useEffect(() => {
    api("/services").then(setServices).catch(() => {});
    refreshUser();
  }, [pathname, refreshUser]);

  const isAdmin = user.role === "admin";
  const pct =
    user.token_limit > 0 ? Math.min(100, Math.round((user.tokens_used * 100) / user.token_limit)) : 100;
  const remaining = Math.max(user.token_limit - user.tokens_used, 0);

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>🌋 Turismo GT</h1>
        <div className="who">
          <strong>{user.full_name}</strong>
          <small>{isAdmin ? "Administrador" : "Turista"}</small>
        </div>

        <nav>
          <div className="nav-title">Servicios de IA</div>
          {services
            .filter((s) => s.is_active && ROUTES[s.code])
            .map((s) => (
              <NavLink key={s.id} to={ROUTES[s.code]}>{s.name}</NavLink>
            ))}

          <div className="nav-title">Mi cuenta</div>
          <NavLink to="/history">Historial de conversaciones</NavLink>
          <NavLink to="/usage">Mi consumo de tokens</NavLink>

          {isAdmin && (
            <>
              <div className="nav-title">Administración</div>
              <NavLink to="/admin/report">Reporte de uso</NavLink>
              <NavLink to="/admin/users">Usuarios</NavLink>
              <NavLink to="/admin/destinations">Destinos</NavLink>
              <NavLink to="/admin/activities">Actividades</NavLink>
              <NavLink to="/admin/services">Servicios de IA</NavLink>
              <NavLink to="/admin/knowledge">Base de conocimiento</NavLink>
              <NavLink to="/admin/api-keys">API keys</NavLink>
            </>
          )}
          <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">API (Swagger) ↗</a>
        </nav>

        <div className="tokens">
          <div className="row-between">
            <small>Tokens</small>
            <small>{fmtNum(user.tokens_used)} / {fmtNum(user.token_limit)}</small>
          </div>
          <div className="bar">
            <div className={pct >= 90 ? "bar-fill danger" : "bar-fill"} style={{ width: `${pct}%` }} />
          </div>
          <small>Disponibles: {fmtNum(remaining)}</small>
        </div>
        <button className="btn secondary" onClick={logout}>Cerrar sesión</button>
      </aside>

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}