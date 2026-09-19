# Tests

- `backend/`: Python unit and integration tests.
- `voice/`: Pipecat text pipeline and flow tests.
- `web/`: Vitest component and API client tests.
- `e2e/`: Playwright browser tests.

From the repository root:

- Python: `python -m pytest` using the voice server environment with backend installed.
- JavaScript dependencies: `npm install` (root workspace).
- Web: `npm test`.
- Browser: `npm run test:e2e` (ports 3090 and 8091 must be free).

Scenario data and recorded evaluation results remain in `evals/`.
