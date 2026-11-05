import { useState } from "react";
import { api } from "../../api.js";
import { Field, Modal, Status } from "../../components/ui.jsx";
import { useLoad } from "../../hooks.js";

function DestForm({ initial, onSaved, onClose }) {
  const [f, setF] = useState({
    name: initial.name || "",
    department: initial.department || "",
    category: initial.category || "",
    description: initial.description || "",
  });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const saved = initial.id
        ? await api(`/destinations/${initial.id}`, { method: "PUT", body: f })
        : await api("/destinations", { method: "POST", body: f });
      onSaved(saved.indexed);
    } catch (error) {
      setErr(error.message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <Field label="Nombre"><input value={f.name} onChange={set("name")} required minLength={2} /></Field>
      <Field label="Departamento"><input value={f.department} onChange={set("department")} required minLength={2} /></Field>
      <Field label="Categoría">
        <input list="dest-cats" value={f.category} onChange={set("category")} required minLength={2} />
        <datalist id="dest-cats">
          {["ciudad", "naturaleza", "arqueología", "aventura", "cultura"].map((c) => <option key={c} value={c} />)}
        </datalist>
      </Field>
      <Field label="Descripción (mínimo 20 caracteres; es el texto que usa el chatbot)">
        <textarea rows={6} value={f.description} onChange={set("description")} required minLength={20} />
      </Field>
      {err && <div className="error">{err}</div>}
      <div className="row">
        <button className="btn" disabled={busy}>{busy ? "Guardando e indexando…" : "Guardar"}</button>
        <button type="button" className="btn ghost" onClick={onClose}>Cancelar</button>
      </div>
    </form>
  );
}

export default function Destinations() {
  const [editing, setEditing] = useState(null);
  const [msg, setMsg] = useState("");
  const { data, error, loading, reload } = useLoad(() => api("/destinations"), []);

  async function remove(d) {
    if (!window.confirm(`¿Eliminar «${d.name}» con todas sus actividades?`)) return;
    try {
      await api(`/destinations/${d.id}`, { method: "DELETE" });
      reload();
    } catch (e) {
      setMsg(e.message);
    }
  }

  return (
    <div>
      <div className="row-between">
        <h2>Destinos</h2>
        <button className="btn" onClick={() => setEditing({})}>+ Nuevo destino</button>
      </div>
      <p className="muted">Estos datos alimentan al chatbot RAG. Al guardar, se regeneran sus fragmentos y embeddings.</p>
      {msg && <div className="notice">{msg}</div>}
      <Status loading={loading} error={error} />
      <div className="card">
        <table className="table">
          <thead><tr><th>Nombre</th><th>Departamento</th><th>Categoría</th><th>Descripción</th><th></th></tr></thead>
          <tbody>
            {(data || []).map((d) => (
              <tr key={d.id}>
                <td>{d.name}</td><td>{d.department}</td><td>{d.category}</td>
                <td className="muted">{d.description.slice(0, 90)}…</td>
                <td className="actions">
                  <button className="btn small" onClick={() => setEditing(d)}>Editar</button>
                  <button className="btn small danger" onClick={() => remove(d)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <Modal title={editing.id ? "Editar destino" : "Nuevo destino"} onClose={() => setEditing(null)}>
          <DestForm
            initial={editing}
            onClose={() => setEditing(null)}
            onSaved={(indexed) => {
              setEditing(null);
              setMsg(indexed
                ? "Guardado e indexado en el RAG."
                : "Guardado, pero NO se pudo indexar en el RAG. Ve a «Base de conocimiento» y pulsa Reindexar.");
              reload();
            }}
          />
        </Modal>
      )}
    </div>
  );
}