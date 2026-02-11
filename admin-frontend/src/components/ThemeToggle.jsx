import Button from './Button.jsx';
import { useTheme } from './ThemeProvider.jsx';

export default function ThemeToggle({ compact = false }) {
  const { theme, toggleTheme } = useTheme();
  const nextTheme = theme === 'dark' ? 'light' : 'dark';

  return (
    <Button
      variant="secondary"
      onClick={toggleTheme}
      className={compact ? 'theme-toggle theme-toggle-compact' : 'theme-toggle'}
      title={`Переключить тему на ${nextTheme === 'dark' ? 'тёмную' : 'светлую'}`}
    >
      {theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
    </Button>
  );
}
