export default function TopBar({ title, right, subtitle }) {
  return (
    <div className="topbar">
      <div>
        <div className="topbar-title">{title}</div>
        {subtitle ? <div className="topbar-subtitle">{subtitle}</div> : null}
      </div>
      <div className="topbar-right">
        {right}
      </div>
    </div>
  );
}
