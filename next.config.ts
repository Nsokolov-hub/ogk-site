import type { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  // Отдельная папка сборки (NEXT_DIST_DIR=.next-prod) — чтобы проверочная сборка не мешала dev-серверу
  distDir: process.env.NEXT_DIST_DIR || '.next',
  // URL-01: все адреса со слешем на конце
  trailingSlash: true,
  poweredByHeader: false,
  // API сайта (backend/): в разработке Next проксирует /api/v1/* на API_ORIGIN, в production его отдаёт Caddy
  async rewrites() {
    const api = process.env.API_ORIGIN ?? 'http://127.0.0.1:8001';
    return [{ source: '/api/v1/:path*', destination: `${api}/api/v1/:path*` }];
  },
  images: {
    formats: ['image/avif', 'image/webp'],
    dangerouslyAllowSVG: true,
    contentDispositionType: 'attachment',
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
};

export default withNextIntl(nextConfig);
