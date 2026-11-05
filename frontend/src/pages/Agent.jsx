import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import Markdown from "../components/Markdown.jsx";
import Steps from "../components/Steps.jsx";
import { fmtNum } from "../utils.js";

const PLAN_EXAMPLE =
  "Día 1: Paseo en lancha entre pueblos (Q100, 5 h) y Cooperativa de tejidos en San Juan (Q30, 2 h). " +
  "Día 2: Kayak al amanecer (Q120, 3 h) en el Lago de Atitlán. Total: Q250 por persona.";

const CONFIG = {
  itinerary: {
    title: "Planificador de itinerarios",
    help: "Describe tu viaje: destinos, días, personas, intereses y presupuesto por persona. El agente busca actividades, consulta el clima y las distancias, y calcula el costo.",
    endpoint: "/ai/itinerary",
    example: { message: "Quiero un viaje de 2 días por el Lago de Atitlán con un presupuesto de Q300 por persona. Me gustan la cultura y la naturaleza." },
  },
  adjust: {
    title: "Ajustador de plan",
    help: "Pega un plan existente e indica qué cambió (presupuesto, clima...). El agente busca alternativas y reajusta las actividades.",
    endpoint: "/ai/adjust-plan",
    example: { plan: PLAN_EXAMPLE, change: "El presupuesto bajó a Q150 por persona" },
  },
};

export default function Agent({ kind }) {
  const cfg = CONFIG[kind];
  const { refreshUser } = useAuth();
  const [values, setValues] = useState({ message: "", plan: "", change: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const set = (k) => (e) => setValues({ ...values, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);
    const body = kind === "itinerary" ? { message: values.message } : { plan: values.plan, change: values.change };
    try {
      setResult(await api(cfg.endpoint, { method: "POST", body }));
      refreshUser();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2>{cfg.title}</h2>
      <p className="muted">{cfg.help}</p>

      <form className="card" onSubmit={submit}>
        {kind === "itinerary" ? (
          <label className="field">
            <span>Tu solicitud</span>
            <textarea rows={4} value={values.message} onChange={set("message")} required minLength={5} maxLength={1000} />
          </label>
        ) : (
          <>
            <label className="field">
              <span>Plan actual</span>
              <textarea rows={5} value={values.plan} onChange={set("plan")} required minLength={20} maxLength={8000} />
            </label>
            <label className="field">
              <span>¿Qué cambió?</span>
              <textarea rows={2} value={values.change} onChange={set("change")} required minLength={3} maxLength={500} />
            </label>
          </>
        )}
        <div className="row">
          <button className="btn" disabled={loading}>{loading ? "El agente está trabajando…" : "Enviar"}</button>
          <button type="button" className="btn ghost" onClick={() => setValues({ message: "", plan: "", change: "", ...cfg.example })}>
            Usar ejemplo
          </button>
        </div>
        {loading && <p className="muted">Esto puede tardar hasta 40 segundos: el agente consulta varias fuentes.</p>}
      </form>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="card">
          <div className="row-between">
            <h3>Resultado</h3>
            <small className="muted">
              {fmtNum(result.usage.total_tokens)} tokens · te quedan {fmtNum(result.tokens_remaining)}
            </small>
          </div>
          <Markdown>{result.answer}</Markdown>
        </div>
      )}
      {result && result.steps.length > 0 && (
        <div className="card">
          <Steps steps={result.steps} />
        </div>
      )}
    </div>
  );
}