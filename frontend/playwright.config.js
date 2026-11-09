import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests: a real browser drives the real app.
 *
 * Playwright starts its OWN servers on other ports with a separate database
 * (backend/e2e.sqlite3, wiped at every run), so your development data and
 * your running dev servers (8000 / 5173) are never touched.
 *
 * Local run (Windows):  activate backend\.venv first, then in frontend\:
 *     npx playwright install chromium     (once)
 *     npm run test:e2e
 */
const BACKEND_PORT = 8765;
const FRONTEND_PORT = 5174;
const python = process.env.E2E_PYTHON || "python";

export default defineConfig({
  testDir: "./e2e",
  workers: 1, // the tests share one server and database
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    locale: "ar",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH }
      : {},
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Fresh database, then Django (HTTP + WebSocket).
      command:
        `${python} manage.py migrate --noinput && ` +
        `${python} manage.py flush --noinput && ` +
        `${python} manage.py runserver ${BACKEND_PORT} --noreload`,
      cwd: "../backend",
      url: `http://127.0.0.1:${BACKEND_PORT}/api/health/`,
      env: {
        DATABASE_URL: "sqlite:///e2e.sqlite3",
        DJANGO_DEBUG: "True",
        DJANGO_SECRET_KEY: "e2e-tests-only-not-a-real-secret",
        FRONTEND_ORIGIN: `http://localhost:${FRONTEND_PORT}`,
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npx vite --port ${FRONTEND_PORT} --strictPort`,
      url: `http://localhost:${FRONTEND_PORT}`,
      env: { BACKEND_URL: `http://127.0.0.1:${BACKEND_PORT}` },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
