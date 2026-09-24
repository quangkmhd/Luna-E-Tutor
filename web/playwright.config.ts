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
      command: `ENV=test TUTOR_LLM_MODE=fixture TUTOR_CURRICULUM_ROOT=../tests/e2e/fixtures/curriculum ALLOWED_ORIGINS=http://localhost:${webPort} uv run uvicorn luna_tutor.api.lesson_runtime:build_lesson_runtime_app --factory --host 127.0.0.1 --port ${apiPort}`,
      cwd: '../backend', port: Number(apiPort), reuseExistingServer: false,
    },
    { command: `VPS_HOST=http://127.0.0.1 BACKEND_PORT=${apiPort} NEXT_PUBLIC_TUTOR_API_URL= npm run dev -- --hostname localhost --port ${webPort}`, port: Number(webPort), reuseExistingServer: false },
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
