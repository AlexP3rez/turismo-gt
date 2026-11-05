import { useState } from "react";
import { api } from "../../api.js";
import { Field, Modal, Status } from "../../components/ui.jsx";
import { useLoad } from "../../hooks.js";

export default function Services() {
  const { data, error, loading, reload } = useLoad(() => api("/services"), []);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", description: "" });
  const [msg, setMsg] = useState("");

  async function toggle(s) {
    try {
      await api(`/admin/services/${s.id}`, { method: "PATCH", body: { is_active: !s.is_active } });
      reload();
    } catch (e) {
      setMsg(e.message);
    }
  }

  function open(s) {
    setForm({ name: s.name, description: s.description || "" });
    setEditing(s);
  }

  async function save(e) {
    e.preventDefault();
    try {
      await api(`/admin/services/${editing.id}`, { method: "PATCH", body: form });
      setEditing(null);
      reload();
    } catch (err) {
      setMsg(err.message);
    }
  }

  return (
    <div>
      <h2>Servicios de IA</h2>
      <p className="muted">Un servicio desactivado desaparece del menú y su API responde 403.</p>
      {msg && <div className="notice">{msg}</div>}
      <Status loading={loading} error={error} />
      <div className="card">
        <table className="table">
          <thead><tr><th>Código</th><th>Nombre</th><th>Descripción</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {(data || []).map((s) => (
              <tr key={s.id}>
                <td><code>{s.code}</code></td><td>{s.name}</td><td className="muted">{s.description}</td>
                <td><span className={`badge ${s.is_active ? "on" : "off"}`}>{s.is_active ? "Activo" : "Desactivado"}</span></td>
                <td className="actions">
                  <button className="btn small" onClick={() => toggle(s)}>{s.is_active ? "Desactivar" : "Activar"}</button>
                  <button className="btn small secondary" onClick={() => open(s)}>Editar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <Modal title="Configurar servicio" onClose={() => setEditing(null)}>
          <form onSubmit={save}>
            <Field label="Nombre"><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required minLength={2} /></Field>
            <Field label="Descripción"><textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
            <div className="row">
              <button className="btn">Guardar</button>
              <button type="button" className="btn ghost" onClick={() => setEditing(null)}>Cancelar</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}