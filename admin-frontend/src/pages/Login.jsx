import { useMemo, useState } from 'react';
import Card from '../components/Card.jsx';
import Button from '../components/Button.jsx';
import Spinner from '../components/Spinner.jsx';
import { Field, Input } from '../components/Field.jsx';
import { adminLogin } from '../lib/adminAuth.js';
import { navigate } from '../lib/router.js';
import { useToast } from '../components/Toast.jsx';
import ThemeToggle from '../components/ThemeToggle.jsx';

export default function LoginPage() {
  const toast = useToast();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const canSubmit = useMemo(
    () => username.trim().length >= 2 && password.trim().length >= 2 && !busy,
    [username, password, busy]
  );

  async function onSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setError('');
    setBusy(true);
    try {
      await adminLogin(username.trim(), password);
      toast.push('Успешный вход', 'success');
      navigate('/trainings');
    } catch (e) {
      const msg = e?.message || 'Ошибка входа';
      setError(msg);
      toast.push(msg, 'error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="center-wrap">
      <Card className="login-card">
        <div className="login-theme-row">
          <ThemeToggle compact />
        </div>

        <div className="login-title">Админ-панель Elmir Volley</div>
        <div className="login-sub">Вход для управления тренировками, игроками и рассылками</div>

        {error ? <div className="alert alert-error">{error}</div> : null}

        <form onSubmit={onSubmit} className="login-form">
          <Field label="Логин">
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              autoComplete="username"
              disabled={busy}
            />
          </Field>

          <Field label="Пароль">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              disabled={busy}
            />
          </Field>

          <Button type="submit" disabled={!canSubmit} className="w-full">
            {busy ? (
              <span className="inline-flex items-center gap-8">
                <Spinner size={18} />
                Входим...
              </span>
            ) : (
              'Войти'
            )}
          </Button>
        </form>

        <div className="login-hint">
          Логин/пароль берутся из `.env.dev`: `ADMIN_USERNAME` и `ADMIN_PASSWORD`.
        </div>
      </Card>
    </div>
  );
}
