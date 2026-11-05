import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ email: "", full_name: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form.email, form.full_name, form.password);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login" onSubmit={submit}>
        <h2>🌋 Turismo GT</h2>
        <p className="muted">
          {mode === "login" ? "Inicia sesión para usar los servicios de IA" : "Crea tu cuenta de turista"}
        </p>
        {mode === "register" && (
          <label className="field">
            <span>Nombre completo</span>
            <input value={form.full_name} onChange={set("full_name")} required minLength={2} />
          </label>
        )}
        <label className="field">
          <span>Correo</span>
          <input type="email" value={form.email} onChange={set("email")} required />
        </label>
        <label className="field">
          <span>Contraseña {mode === "register" && "(mínimo 8 caracteres)"}</span>
          <input type="password" value={form.password} onChange={set("password")} required minLength={mode === "register" ? 8 : 1} />
        </label>
        {error && <div className="error">{error}</div>}
        <button className="btn" disabled={busy}>
          {busy ? "Un momento…" : mode === "login" ? "Entrar" : "Registrarme"}
        </button>
        <button
          type="button"
          className="btn ghost"
          onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
        >
          {mode === "login" ? "¿No tienes cuenta? Regístrate" : "Ya tengo cuenta"}
        </button>
      </form>
    </div>
  );
}