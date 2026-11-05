import { useState } from "react";
import { api } from "../../api.js";
import { Field, Modal, Status } from "../../components/ui.jsx";
import { useLoad } from "../../hooks.js";

function ActForm({ initial, destinations, onSaved, onClose }) {
  const isNew = !initial.id;
  const [f, setF] = useState({
    destination_id: initial.destination_id || destinations[0]?.id || "",
    name: initial.name || "",
    description: initial.description || "",
    category: initial.category || "",
    est_cost_gtq: initial.est_cost_gtq ?? 0,
    duration_hours: initial.duration_hours ?? 2,
    latitude: initial.latitude ?? "",
    longitude: initial.longitude ?? "",
  });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    const body = {
      name: f.name,
      description: f.description || null,
      category: f.category,
      est_cost_gtq: Number(f.est_cost_gtq),
      duration_hours: Number(f.duration_hours),
      latitude: f.latitude === "" ? null : Number(f.latitude),
      longitude: f.longitude === "" ? null : Number(f.longitude),
    };
    try {
      const saved = isNew
        ? await api("/activities", { method: "POST", body: { ...body, destination_id: Number(f.destination_id) } })
        : await api(`/activities/${initial.id}`, { method: "PUT", body });
      onSaved(saved.indexed);
    } catch (error) {
      setErr(error.message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <Field label="Destino">
        <select value={f.destination_id} onChange={set("destination_id")} disabled={!isNew} required>
          {destinations.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </Field>
      <Field label="Nombre"><input value={f.name} onChange={set("name")} required minLength={2} /></Field>
      <Field label="Descripción"><textarea rows={3} value={f.description} onChange={set("description")} /></Field>
      <Field label="Categoría">
        <input list="act-cats" value={f.category} onChange={set("category")} required minLength={2} />
        <datalist id="act-cats">
          {["cultura", "naturaleza", "aventura", "gastronomía", "arqueología"].map((c) => <option key={c} value={c} />)}
        </datalist>
      </Field>
      <div className="grid2">
        <Field label="Costo aproximado (Q)"><input type="number" step="any" min={0} value={f.est_cost_gtq} onChange={set("est_cost_gtq")} required /></Field>
        <Field label="Duración (horas)"><input type="number" step="any" min={0.5} max={99} value={f.duration_hours} onChange={set("duration_hours")} required /></Field>
        <Field label="Latitud (opcional)"><input type="number" step="any" value={f.latitude} onChange={set("latitude")} /></Field>
        <Field label="Longitud (opcional)"><input type="number" step="any" value={f.longitude} onChange={set("longitude")} /></Field>
      </div>
      {err && <div className="error">{err}</div>}
      <div className="row">
        <button className="btn" disabled={busy}>{busy ? "Guardando e indexando…" : "Guardar"}</button>
        <button type="button" className="btn ghost" onClick={onClose}>Cancelar</button>
      </div>
    </form>
  );
}

export default function Activities() {
  const [dest, setDest] = useState("");
  const [editing, setEditing] = useState(null);
  const [msg, setMsg] = useState("");
  const dests = useLoad(() => api("/destinations"), []);
  const acts = useLoad(() => api("/activities", { params: { destination_id: dest } }), [dest]);
  const nameOf = (id) => (dests.data || []).find((d) => d.id === id)?.name || id;

  async function remove(a) {
    if (!window.confirm(`¿Eliminar la actividad «${a.name}»?`)) return;
    try {
      await api(`/activities/${a.id}`, { method: "DELETE" });
      acts.reload();
    } catch (e) {
      setMsg(e.message);
    }
  }

  return (
    <div>
      <div className="row-between">
        <h2>Actividades</h2>
        <button className="btn" disabled={!dests.data} onClick={() => setEditing({})}>+ Nueva actividad</button>
      </div>
      <div className="row">
        <select value={dest} onChange={(e) => setDest(e.target.value)}>
          <option value="">Todos los destinos</option>
          {(dests.data || []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </div>
      {msg && <div className="notice">{msg}</div>}
      <Status loading={acts.loading} error={acts.error} />
      <div className="card">
        <table className="table">
          <thead><tr><th>Destino</th><th>Actividad</th><th>Categoría</th><th>Costo</th><th>Horas</th><th></th></tr></thead>
          <tbody>
            {(acts.data || []).map((a) => (
              <tr key={a.id}>
                <td>{nameOf(a.destination_id)}</td><td>{a.name}</td><td>{a.category}</td>
                <td>Q{Number(a.est_cost_gtq).toFixed(2)}</td><td>{a.duration_hours}</td>
                <td className="actions">
                  <button className="btn small" onClick={() => setEditing(a)}>Editar</button>
                  <button className="btn small danger" onClick={() => remove(a)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <Modal title={editing.id ? "Editar actividad" : "Nueva actividad"} onClose={() => setEditing(null)}>
          <ActForm
            initial={editing}
            destinations={dests.data || []}
            onClose={() => setEditing(null)}
            onSaved={(indexed) => {
              setEditing(null);
              setMsg(indexed ? "Guardado e indexado en el RAG." : "Guardado, pero NO se pudo indexar en el RAG. Usa «Base de conocimiento» para reindexar.");
              acts.reload();
            }}
          />
        </Modal>
      )}
    </div>
  );
}