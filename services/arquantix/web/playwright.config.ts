import { defineConfig, devices } from '@playwright/test'

/**
 * E2E minimal — multilingue (`e2e/multilingual.spec.ts`).
 *
 * Prérequis : `npm run dev` (ou laisser webServer démarrer), DB avec seed incluant la page `e2e-smoke`.
 *
 * Variables :
 * - `PLAYWRIGHT_BASE_URL` — défaut http://127.0.0.1:3000
 * - `PLAYWRIGHT_SKIP_WEBSERVER=1` — ne pas lancer `next dev` (serveur déjà up)
 */
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3000'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: 'npm run dev',
        url: baseURL,
        reuseExistingServer: true,
        timeout: 120_000,
      },
})
