import { useEffect, useMemo, useState } from 'react';
import LoginPage from './pages/Login.jsx';
import TrainingsPage from './pages/Trainings.jsx';
import TrainingFormPage from './pages/TrainingForm.jsx';
import PlayersPage from './pages/Players.jsx';
import PlayerDetailsPage from './pages/PlayerDetails.jsx';
import NotificationsAdminPage from './pages/NotificationsAdmin.jsx';
import AuditLogsPage from './pages/AuditLogs.jsx';
import SettingsPage from './pages/Settings.jsx';
import Card from './components/Card.jsx';
import Spinner from './components/Spinner.jsx';
import { matchRoute, navigate, useLocation } from './lib/router.js';
import { ensureSession, isAuthenticated } from './lib/adminAuth.js';

function NotFound() {
  return (
    <div className="page">
      <Card>
        <div className="h1">Страница не найдена</div>
        <div className="muted">Проверьте адрес и попробуйте снова.</div>

        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={() => navigate('/', { replace: true })}>На главную</button>
          <button className="btn btn-secondary" onClick={() => navigate('/trainings', { replace: true })}>Тренировки</button>
        </div>
      </Card>
    </div>
  );
}

function Protected({ children }) {
  const [checking, setChecking] = useState(true);
  const [ok, setOk] = useState(false);

  useEffect(() => {
    let alive = true;

    (async () => {
      try {
        const result = await ensureSession();
        if (alive) setOk(Boolean(result));
      } catch {
        if (alive) setOk(false);
      }
      if (alive) {
        setChecking(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!checking && !ok) navigate('/login', { replace: true });
  }, [checking, ok]);

  if (checking) {
    return (
      <div className="center-wrap">
        <Card className="login-card">
          <div className="inline-flex items-center gap-10">
            <Spinner size={18} />
            Проверяем сессию...
          </div>
        </Card>
      </div>
    );
  }

  if (!ok) return null;
  return children;
}

export default function App() {
  const loc = useLocation();

  const route = useMemo(() => {
    const path = loc.pathname || '/';
    if (path === '/') return { pattern: '/', params: {}, pathname: '/' };

    return (
      matchRoute(path, '/login') ||
      matchRoute(path, '/trainings') ||
      matchRoute(path, '/trainings/new') ||
      matchRoute(path, '/trainings/:id') ||
      matchRoute(path, '/players') ||
      matchRoute(path, '/players/:id') ||
      matchRoute(path, '/notifications') ||
      matchRoute(path, '/audit-logs') ||
      matchRoute(path, '/settings') ||
      { pattern: '404', params: {}, pathname: path }
    );
  }, [loc.pathname]);

  useEffect(() => {
    if (route.pattern !== '/') return;
    if (isAuthenticated()) navigate('/trainings', { replace: true });
    else navigate('/login', { replace: true });
  }, [route.pattern]);

  if (route.pattern === '/login') return <LoginPage />;

  if (route.pattern === '/trainings') {
    return (
      <Protected>
        <TrainingsPage />
      </Protected>
    );
  }

  if (route.pattern === '/trainings/new') {
    return (
      <Protected>
        <TrainingFormPage mode="create" />
      </Protected>
    );
  }

  if (route.pattern === '/trainings/:id') {
    return (
      <Protected>
        <TrainingFormPage mode="edit" trainingId={route.params.id} routeState={loc.state} />
      </Protected>
    );
  }

  if (route.pattern === '/players') {
    return (
      <Protected>
        <PlayersPage />
      </Protected>
    );
  }

  if (route.pattern === '/players/:id') {
    return (
      <Protected>
        <PlayerDetailsPage userId={route.params.id} />
      </Protected>
    );
  }

  if (route.pattern === '/notifications') {
    return (
      <Protected>
        <NotificationsAdminPage />
      </Protected>
    );
  }

  if (route.pattern === '/audit-logs') {
    return (
      <Protected>
        <AuditLogsPage />
      </Protected>
    );
  }

  if (route.pattern === '/settings') {
    return (
      <Protected>
        <SettingsPage />
      </Protected>
    );
  }

  return <NotFound />;
}
