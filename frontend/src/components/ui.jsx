export function Modal({ title, onClose, children }) {
  return (
    <div className="modal-bg" onMouseDown={onClose}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="row-between">
          <h3>{title}</h3>
          <button type="button" className="btn ghost" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export function Status({ loading, error }) {
  if (loading) return <p className="muted">Cargando…</p>;
  if (error) return <div className="error">{error}</div>;
  return null;
}