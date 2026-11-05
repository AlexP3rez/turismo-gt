import { useState } from "react";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { Field, Modal, Status } from "../../components/ui.jsx";
import { useLoad } from "../../hooks.js";
import { fmtNum } from "../../utils.js";

function UserForm({ initial, isSelf, onSaved, onClose }) {
  const isNew = !initial.id;
  const [f, setF] = useState({
    email: initial.email || "",
    full_name: initial.full_name || "",
    password: "",
    role: initial.role || "user",
    token_limit: initial.token_limit ?? 20000,
    is_active: initial.is_active ?? true,
  });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const body = { email: f.email, full_name: f.full_name, role: f.role, token_limit: Number(f.token_limit) };
      if (f.password) body.password = f.password;
      if (isNew) await api("/admin/users", { method: "POST", body });
      else await api(`/admin/users/${initial.id}`, { method: "PATCH", body: { ...body, is_active: f.is_active } });
      onSaved();
    } catch (error) {
      setErr(error.message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <Field label="Nombre completo"><input value={f.full_name} onChange={set("full_name")} required minLength={2} /></Field>
      <Field label="Correo"><input type="email" value={f.email} onChange={set("email")} required /></Field>
      <Field label={isNew ? "Contraseña (mínimo 8)" : "Nueva contraseña (déjala vacía para no cambiarla)"}>
        <input type="password" value={f.password} onChange={set("password")} required={isNew} minLength={8} />
      </Field>
      <Field label="Rol">
        <select value={f.role} onChange={set("role")} disabled={isSelf}>
          <option value="user">Usuario</option>
          <option value="admin">Administrador</option>
        </select>
      </Field>
      <Field label="Límite de tokens">
        <input type="number" min={0} value={f.token_limit} onChange={set("token_limit")} required />
      </Field>
      {!isNew && (
        <label className="check">
          <input type="checkbox" checked={f.is_active} disabled={isSelf} onChange={(e) => setF({ ...f, is_active: e.target.checked })} />
          Usuario activo
        </label>
      )}
      {err && <div className="error">{err}</div>}
      <div className="row">
        <button className="btn" disabled={busy}>Guardar</button>
        <button type="button" className="btn ghost" onClick={onClose}>Cancelar</button>
      </div>
    </form>
  );
}

export default function Users() {
  const { user: me } = useAuth();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [editing, setEditing] = useState(null);
  const [msg, setMsg] = useState("");
  const { data, error, loading, reload } = useLoad(() => api("/admin/users", { params: { search, role } }), [search, role]);

  async function resetTokens(u) {
    try {
      await api(`/admin/users/${u.id}/reset-tokens`, { method: "POST" });
      setMsg(`Consumo de ${u.email} reiniciado.`);
      reload();
    } catch (e) {
      setMsg(e.message);
    }
  }

  async function remove(u) {
    if (!window.confirm(`¿Eliminar a ${u.email}? Se borrarán también sus conversaciones y consumo.`)) return;
    try {
      await api(`/admin/users/${u.id}`, { method: "DELETE" });
      reload();
    } catch (e) {
      setMsg(e.message);
    }
  }

  return (
    <div>
      <div className="row-between">
        <h2>Usuarios</h2>
        <button className="btn" onClick={() => setEditing({})}>+ Nuevo usuario</button>
      </div>
      <form className="row" onSubmit={(e) => { e.preventDefault(); setSearch(q); }}>
        <input placeholder="Buscar por nombre o correo" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="">Todos los roles</option>
          <option value="user">Usuario</option>
          <option value="admin">Administrador</option>
        </select>
        <button className="btn secondary">Buscar</button>
      </form>
      {msg && <div className="notice">{msg}</div>}
      <Status loading={loading} error={error} />

      <div className="card">
        <table className="table">
          <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Tokens (usados / límite)</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {(data || []).map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td><td>{u.email}</td>
                <td><span className={`badge ${u.role}`}>{u.role === "admin" ? "Admin" : "Usuario"}</span></td>
                <td>{fmtNum(u.tokens_used)} / {fmtNum(u.token_limit)}</td>
                <td>{u.is_active ? "Activo" : "Inactivo"}</td>
                <td className="actions">
                  <button className="btn small" onClick={() => setEditing(u)}>Editar</button>
                  <button className="btn small secondary" onClick={() => resetTokens(u)}>Reiniciar tokens</button>
                  {u.id !== me.id && <button className="btn small danger" onClick={() => remove(u)}>Eliminar</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <Modal title={editing.id ? "Editar usuario" : "Nuevo usuario"} onClose={() => setEditing(null)}>
          <UserForm
            initial={editing}
            isSelf={editing.id === me.id}
            onClose={() => setEditing(null)}
            onSaved={() => { setEditing(null); reload(); }}
          />
        </Modal>
      )}
    </div>
  );
}