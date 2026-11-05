import { useState } from "react";
import { api } from "../api.js";
import { Status } from "../components/ui.jsx";
import { useLoad } from "../hooks.js";
import { SERVICES, fmtDate, fmtNum } from "../utils.js";

export default function MyUsage() {
  const [service, setService] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const params = { service, date_from: from, date_to: to };
  const { data, error, loading } = useLoad(
    () => Promise.all([api("/usage/me", { params }), api("/usage/me/records", { params: { ...params, limit: 50 } })]),
    [service, from, to]
  );
  const [usage, records] = data || [null, []];
  const pct = usage && usage.token_limit > 0 ? Math.min(100, Math.round((usage.tokens_used * 100) / usage.token_limit)) : 0;

  return (
    <div>
      <h2>Mi consumo de tokens</h2>
      <div className="row">
        <select value={service} onChange={(e) => setService(e.target.value)}>
          <option value="">Todos los servicios</option>
          {SERVICES.map((s) => <option key={s.code} value={s.code}>{s.label}</option>)}
        </select>
        <label className="check">Desde <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
        <label className="check">Hasta <input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></label>
      </div>
      <Status loading={loading} error={error} />

      {usage && (
        <>
          <div className="kpis">
            <div className="card kpi"><small>Límite</small><strong>{fmtNum(usage.token_limit)}</strong></div>
            <div className="card kpi"><small>Usados</small><strong>{fmtNum(usage.tokens_used)}</strong></div>
            <div className="card kpi"><small>Disponibles</small><strong>{fmtNum(usage.tokens_remaining)}</strong></div>
            <div className="card kpi"><small>Consultas (filtro)</small><strong>{fmtNum(usage.total_queries)}</strong></div>
          </div>
          <div className="bar big"><div className={pct >= 90 ? "bar-fill danger" : "bar-fill"} style={{ width: `${pct}%` }} /></div>

          <div className="card">
            <h3>Consumo acumulado por servicio</h3>
            <table className="table">
              <thead><tr><th>Servicio</th><th>Consultas</th><th>Entrada</th><th>Salida</th><th>Total</th></tr></thead>
              <tbody>
                {usage.by_service.length === 0 && <tr><td colSpan={5} className="muted">Sin consumo en este filtro.</td></tr>}
                {usage.by_service.map((s) => (
                  <tr key={s.service_code}>
                    <td>{s.service_name}</td><td>{fmtNum(s.queries)}</td>
                    <td>{fmtNum(s.prompt_tokens)}</td><td>{fmtNum(s.completion_tokens)}</td><td>{fmtNum(s.total_tokens)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>Detalle de consultas (últimas 50)</h3>
            <table className="table">
              <thead><tr><th>Fecha</th><th>Servicio</th><th>Entrada</th><th>Salida</th><th>Total</th></tr></thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id}>
                    <td>{fmtDate(r.created_at)}</td><td>{r.service_name}</td>
                    <td>{fmtNum(r.prompt_tokens)}</td><td>{fmtNum(r.completion_tokens)}</td><td>{fmtNum(r.total_tokens)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}