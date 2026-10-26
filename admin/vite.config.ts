import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// В разработке админка на http://127.0.0.1:5174 ходит в API сайта (ADMIN_URL по умолчанию — этот адрес).
// На сервере её статику отдаёт Caddy на ADMIN_DOMAIN, а /api/v1/admin/* проксирует в API (deploy/caddy/admin.caddy).
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    proxy: { '/api': process.env.API_ORIGIN ?? 'http://127.0.0.1:8001' },
  },
  build: { outDir: 'dist', sourcemap: false },
});
