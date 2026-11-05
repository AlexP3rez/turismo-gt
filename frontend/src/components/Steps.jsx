/** Pasos intermedios de un agente: herramienta, argumentos y resultado. */
export default function Steps({ steps }) {
  if (!steps || steps.length === 0) return null;
  return (
    <div className="steps">
      <h4>Pasos del agente ({steps.length})</h4>
      {steps.map((s) => (
        <details key={s.step}>
          <summary>
            <span className="badge">{s.step}</span> <code>{s.tool}</code>
          </summary>
          <p className="muted">Argumentos</p>
          <pre>{JSON.stringify(s.arguments, null, 2)}</pre>
          <p className="muted">Resultado</p>
          <pre>{s.result}</pre>
        </details>
      ))}
    </div>
  );
}