import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '../tests/e2e',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: 'http://localhost:3090', trace: 'retain-on-failure' },
  webServer: [
    {
      command: "rm -f /tmp/luna-tutor-e2e.sqlite3 && ENV=test TUTOR_LLM_MODE=fixture TUTOR_DATABASE_PATH=/tmp/luna-tutor-e2e.sqlite3 uv run uvicorn luna_tutor.api.runtime:build_runtime_app --factory --host 127.0.0.1 --port 8091",
      cwd: '../backend', port: 8091, reuseExistingServer: false,
    },
    { command: 'NEXT_PUBLIC_TUTOR_API_URL=http://localhost:8091 npm run dev -- --hostname localhost --port 3090', port: 3090, reuseExistingServer: false },
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
