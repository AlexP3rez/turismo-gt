import { useState } from "react";
import { api } from "../../api.js";
import { Status } from "../../components/ui.jsx";
import { useLoad } from "../../hooks.js";
import { fmtDate } from "../../utils.js";

export default function ApiKeys() {
  const { data, error, loading, reload } = useLoad(() => api("/admin/api-keys"), []);
  const [name, setName] = useState("");
  const [created, setCreated] = useState(null);
  const [msg, setMsg] = useState("");

  async function create(e) {
    e.preventDefault();
    setMsg("");
    try {
      setCreated(await api("/admin/api-keys", { method: "POST", body: { name } }));
      setName("");
      reload();
    } catch (err) {
      setMsg(err.message);
    }
  }

  async function revoke(k) {
    if (!window.confirm(`¿Revocar la llave «${k.name}»? Dejará de funcionar de inmediato.`)) return;
    try {
      await api(`/admin/api-keys/${k.id}`, { method: "DELETE" });
      reload();
    } catch (err) {
      setMsg(err.message);
    }
  }

  return (
    <div>
      <h2>API keys (solo lectura)</h2>
      <p className="muted">Sirven para que Power BI u otros clientes consulten <code>/reports/*</code> sin iniciar sesión. No pueden usar la IA ni modificar datos.</p>

      <form className="row" onSubmit={create}>
        <input placeholder="Nombre de la llave (p. ej. Power BI)" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
        <button className="btn">Crear llave</button>
      </form>

      {created && (
        <div className="notice">
          <strong>Copia esta llave ahora: no se volverá a mostrar.</strong>
          <pre>{created.api_key}</pre>
          <button className="btn small" onClick={() => navigator.clipboard.writeText(created.api_key)}>Copiar</button>{" "}
          <button className="btn small ghost" onClick={() => setCreated(null)}>Ocultar</button>
        </div>
      )}
      {msg && <div className="error">{msg}</div>}
      <Status loading={loading} error={error} />

      <div className="card">
        <table className="table">
          <thead><tr><th>Nombre</th><th>Creada</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {(data || []).map((k) => (
              <tr key={k.id}>
                <td>{k.name}</td><td>{fmtDate(k.created_at)}</td><td>{k.is_active ? "Activa" : "Inactiva"}</td>
                <td className="actions"><button className="btn small danger" onClick={() => revoke(k)}>Revocar</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}