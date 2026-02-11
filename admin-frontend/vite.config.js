import process from 'node:process';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const DEV_BACKEND = process.env.VITE_DEV_BACKEND_URL || 'http://localhost:8001';
const PROD_BASE = process.env.VITE_BASE_PATH || '/admin/';

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'serve' ? '/' : PROD_BASE,
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': {
        target: DEV_BACKEND,
        changeOrigin: true,
      },
      '/docs': {
        target: DEV_BACKEND,
        changeOrigin: true,
      },
      '/openapi.json': {
        target: DEV_BACKEND,
        changeOrigin: true,
      },
    }
  }
}));
