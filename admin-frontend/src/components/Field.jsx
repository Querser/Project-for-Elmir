export function Field({ label, hint, error, children }) {
  return (
    <div className="field">
      {label ? <div className="field-label">{label}</div> : null}
      {children}
      {hint ? <div className="field-hint">{hint}</div> : null}
      {error ? <div className="field-error">{error}</div> : null}
    </div>
  );
}

export function Input(props) {
  return <input {...props} className={`input ${props.className || ''}`} />;
}

export function Textarea(props) {
  return <textarea {...props} className={`input textarea ${props.className || ''}`} />;
}

export function Select(props) {
  return <select {...props} className={`input ${props.className || ''}`} />;
}
