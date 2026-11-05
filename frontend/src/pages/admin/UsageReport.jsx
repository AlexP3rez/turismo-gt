import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../../api.js";
import { Status } from "../../components/ui.jsx";
import { useLoad } from "../../hooks.js";
import { SERVICES, SHORT, fmtNum } from "../../utils.js";

export default function UsageReport() {
  const [userId, setUserId] = useState("");
  const [service, setService] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const users = useLoad(() => api("/admin/users"), []);
  const params = { user_id: userId, service, date_from: from, date_to: to };
  // Son los mismos endpoints que consumirá Power BI
  const report = useLoad(
    () => Promise.all([api("/reports/summary", { params }), api("/reports/usage", { params })]),
    [userId, service, from, to]
  );
  const [summary, rows] = report.data || [[], []];

  const chart = summary.map((s) => ({ name: SHORT[s.service_code] || s.service_name, consultas: s.queries, tokens: s.total_tokens }));
  const totalQueries = summary.reduce((a, s) => a + s.queries, 0);
  const totalTokens = summary.reduce((a, s) => a + s.total_tokens, 0);

  return (
    <div>
      <h2>Reporte de uso</h2>
      <p className="muted">Consultas realizadas y consumo acumulado por servicio. Usa los mismos endpoints que el reporte de Power BI.</p>
      <div className="row">
        <select value={userId} onChange={(e) => setUserId(e.target.value)}>
          <option value="">Todos los usuarios</option>
          {(users.data || []).map((u) => <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>)}
        </select>
        <select value={service} onChange={(e) => setService(e.target.value)}>
          <option value="">Todos los servicios</option>
          {SERVICES.map((s) => <option key={s.code} value={s.code}>{s.label}</option>)}
        </select>
        <label className="check">Desde <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
        <label className="check">Hasta <input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></label>
      </div>
      <Status loading={report.loading} error={report.error} />

      <div className="kpis">
        <div className="card kpi"><small>Consultas</small><strong>{fmtNum(totalQueries)}</strong></div>
        <div className="card kpi"><small>Tokens consumidos</small><strong>{fmtNum(totalTokens)}</strong></div>
      </div>

      <div className="charts">
        <div className="card">
          <h3>Consultas por servicio</h3>
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip />
                <Bar dataKey="consultas" fill="#0f766e" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <h3>Tokens por servicio</h3>
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" /><YAxis /><Tooltip />
                <Bar dataKey="tokens" fill="#b45309" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Detalle por día, servicio y usuario</h3>
        <table className="table">
          <thead><tr><th>Día</th><th>Servicio</th><th>Usuario</th><th>Consultas</th><th>Entrada</th><th>Salida</th><th>Total</th></tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={7} className="muted">Sin datos para este filtro.</td></tr>}
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.day}</td><td>{r.service_name}</td><td>{r.user_email}</td><td>{fmtNum(r.queries)}</td>
                <td>{fmtNum(r.prompt_tokens)}</td><td>{fmtNum(r.completion_tokens)}</td><td>{fmtNum(r.total_tokens)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}