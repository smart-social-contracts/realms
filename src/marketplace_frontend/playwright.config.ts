import { defineConfig, devices } from '@playwright/test';

// Smoke spec for the marketplace_frontend SPA. The default base URL
// assumes a local dfx replica with marketplace_frontend deployed and
// reachable at http://<canister>.localhost:4943/. CI/dev should set
// PLAYWRIGHT_BASE_URL to that URL before running `npx playwright test`.
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4943/',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
    headless: true,
    // Use Chrome from /usr/local/bin if present (CI image), otherwise let
    // Playwright fall back to its bundled chromium.
    launchOptions: process.env.MARKETPLACE_E2E_USE_LOCAL_CHROME
      ? { executablePath: '/usr/local/bin/google-chrome', args: ['--no-sandbox', '--disable-dev-shm-usage'] }
      : {},
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
