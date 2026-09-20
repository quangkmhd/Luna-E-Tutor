import { defineConfig, devices } from '@playwright/test';

const apiPort = process.env.E2E_API_PORT ?? '8091';
const webPort = process.env.E2E_WEB_PORT ?? '3090';

export default defineConfig({
  testDir: '../tests/e2e',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: `http://localhost:${webPort}`, trace: 'retain-on-failure' },
  webServer: [
    {
      command: `rm -f /tmp/luna-tutor-e2e.sqlite3 && ENV=test E2E_WEB_ORIGIN=http://localhost:${webPort} TUTOR_LLM_MODE=fixture TUTOR_DATABASE_PATH=/tmp/luna-tutor-e2e.sqlite3 uv run uvicorn luna_tutor.api.runtime:build_runtime_app --factory --host 127.0.0.1 --port ${apiPort}`,
      cwd: '../backend', port: Number(apiPort), reuseExistingServer: false,
    },
    { command: `NEXT_PUBLIC_TUTOR_API_URL=http://localhost:${apiPort} npm run dev -- --hostname localhost --port ${webPort}`, port: Number(webPort), reuseExistingServer: false },
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
