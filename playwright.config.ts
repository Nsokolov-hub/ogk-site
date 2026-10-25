import { defineConfig } from '@playwright/test';

/**
 * E2E сценариев SC-01…SC-04 (NFR-12) на работающем сайте: витрина, API, PostgreSQL и Meilisearch с тестовым
 * каталогом (`python -m app.catalog.cli seed`). Адрес — E2E_BASE_URL (по умолчанию http://localhost:3000).
 * Локально можно взять установленный Chrome: PLAYWRIGHT_CHANNEL=chrome npm run e2e.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    headless: true,
    locale: 'ru-RU',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
});
