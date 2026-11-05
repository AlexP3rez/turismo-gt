import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import Markdown from "../components/Markdown.jsx";
import Steps from "../components/Steps.jsx";
import { Status } from "../components/ui.jsx";
import { useLoad } from "../hooks.js";
import { SERVICES, fmtDate, fmtNum, stripCitations } from "../utils.js";

export default function History() {
  const { user } = useAuth();
  const [all, setAll] = useState(false); // solo admin: ver conversaciones de todos
  const [service, setService] = useState("");
  const [selected, setSelected] = useState(null);

  const base = all ? "/admin/history/conversations" : "/history/conversations";
  const list = useLoad(() => api(base, { params: { service, limit: 100 } }), [base, service]);
  const detail = useLoad(
    () => (selected ? api(`${base}/${selected}`) : Promise.resolve(null)),
    [base, selected]
  );

  const conv = detail.data;

  return (
    <div>
      <h2>Historial de conversaciones</h2>
      <div className="row">
        <select value={service} onChange={(e) => setService(e.target.value)}>
          <option value="">Todos los servicios</option>
          {SERVICES.map((s) => <option key={s.code} value={s.code}>{s.label}</option>)}
        </select>
        {user.role === "admin" && (
          <label className="check">
            <input type="checkbox" checked={all} onChange={(e) => { setAll(e.target.checked); setSelected(null); }} />
            Ver las de todos los usuarios
          </label>
        )}
      </div>

      <div className="split">
        <div className="card list">
          <Status loading={list.loading} error={list.error} />
          {(list.data || []).length === 0 && !list.loading && <p className="muted">Aún no hay conversaciones.</p>}
          {(list.data || []).map((c) => (
            <button key={c.id} className={`item ${selected === c.id ? "active" : ""}`} onClick={() => setSelected(c.id)}>
              <strong>{c.title || "(sin título)"}</strong>
              <small>{c.service_name}{all ? ` · ${c.user_email}` : ""}</small>
              <small>{fmtDate(c.created_at)} · {fmtNum(c.total_tokens)} tokens</small>
            </button>
          ))}
        </div>

        <div className="card detail">
          {!selected && <p className="muted">Selecciona una conversación.</p>}
          <Status loading={selected && detail.loading} error={detail.error} />
          {conv && (
            <>
              <h3>{conv.title}</h3>
              <p className="muted">{conv.service_name} · {fmtDate(conv.created_at)} · {fmtNum(conv.total_tokens)} tokens</p>
              {conv.messages.map((m) => (
                <div key={m.id} className={`bubble ${m.role}`}>
                  {m.role === "user" ? m.content : <Markdown>{stripCitations(m.content)}</Markdown>}
                  {m.sources && m.sources.length > 0 && (
                    <div className="sources">
                      <span>Fuentes:</span>
                      {m.sources.map((s) => <span className="chip" key={s.id}>{s.title}</span>)}
                    </div>
                  )}
                  <Steps steps={m.steps} />
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}