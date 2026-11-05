import { useState } from "react";
import { api } from "../../api.js";
import { Status } from "../../components/ui.jsx";
import { useLoad } from "../../hooks.js";

export default function Knowledge() {
  const { data, error, loading, reload } = useLoad(() => api("/admin/knowledge"), []);
  const [busy, setBusy] = useState(null);
  const [msg, setMsg] = useState("");

  async function run(path, key) {
    setBusy(key);
    setMsg("");
    try {
      const r = await api(path, { method: "POST" });
      setMsg(
        r.destinations !== undefined
          ? `Reindexados ${r.destinations} destinos (${r.chunks} fragmentos).`
          : `Destino reindexado (${r.chunks} fragmentos).`
      );
      reload();
    } catch (e) {
      setMsg(e.message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <div className="row-between">
        <h2>Base de conocimiento (RAG)</h2>
        <button className="btn" disabled={busy !== null} onClick={() => run("/admin/knowledge/reindex", "all")}>
          {busy === "all" ? "Reindexando…" : "Reindexar todo"}
        </button>
      </div>
      <p className="muted">Un destino con 0 fragmentos no puede responderse en el chatbot. Reindexa si falló Gemini al guardar.</p>
      {msg && <div className="notice">{msg}</div>}
      <Status loading={loading} error={error} />
      <div className="card">
        <table className="table">
          <thead><tr><th>Destino</th><th>Fragmentos indexados</th><th></th></tr></thead>
          <tbody>
            {(data || []).map((d) => (
              <tr key={d.id}>
                <td>{d.name}</td>
                <td>{d.chunks > 0 ? d.chunks : <span className="badge off">0</span>}</td>
                <td className="actions">
                  <button className="btn small" disabled={busy !== null} onClick={() => run(`/admin/knowledge/reindex/${d.id}`, d.id)}>
                    {busy === d.id ? "Reindexando…" : "Reindexar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}