import Button from './Button.jsx';
import { navigate, useLocation } from '../lib/router.js';
import { adminLogout } from '../lib/adminAuth.js';
import { useToast } from './Toast.jsx';
import ThemeToggle from './ThemeToggle.jsx';

const NAV_ITEMS = [
  { path: '/trainings', label: 'Тренировки' },
  { path: '/players', label: 'Игроки' },
  { path: '/notifications', label: 'Уведомления' },
  { path: '/audit-logs', label: 'Журнал действий' },
  { path: '/settings', label: 'Настройки' },
];

function isActive(pathname, path) {
  if (path === '/trainings') return pathname.startsWith('/trainings');
  if (path === '/players') return pathname.startsWith('/players');
  return pathname === path || pathname.startsWith(`${path}/`);
}

export default function AdminLayout({ title, subtitle, actions, children }) {
  const toast = useToast();
  const loc = useLocation();
  const pathname = String(loc?.pathname || '/');

  function onLogout() {
    adminLogout();
    toast.push('Вы вышли из аккаунта', 'success');
    navigate('/login', { replace: true });
  }

  return (
    <div className="page">
      <div className="topbar">
        <div>
          <div className="h1">{title}</div>
          {subtitle ? <div className="muted">{subtitle}</div> : null}
        </div>
        <div className="topbar-actions">
          {actions}
          <ThemeToggle />
          <Button variant="secondary" onClick={onLogout}>Выйти</Button>
        </div>
      </div>

      <div className="admin-nav" role="tablist" aria-label="Разделы админки">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.path}
            type="button"
            className={`admin-nav-item ${isActive(pathname, item.path) ? 'active' : ''}`}
            onClick={() => navigate(item.path)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {children}
    </div>
  );
}
