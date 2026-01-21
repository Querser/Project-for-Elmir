import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // Читаем .env.* (в т.ч. VITE_BACKEND_TARGET)
  const env = loadEnv(mode, process.cwd(), "");

  // Если не задано — бэкенд из docker-compose.dev.yml по умолчанию на 8001
  const BACKEND_TARGET = env.VITE_BACKEND_TARGET || "http://localhost:8001";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": {
          target: BACKEND_TARGET,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
