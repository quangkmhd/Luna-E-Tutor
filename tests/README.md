# Tests

| Thư mục | Phạm vi | Môi trường chạy |
| --- | --- | --- |
| `backend/` | Python unit/integration tests cho API và teaching core | `backend/.venv` |
| `voice/` | Pipecat text pipeline, voice flow và scripts | `voice/server/.venv` |
| `web/` | Vitest component và API-client tests | Node.js workspace `web/` |
| `e2e/` | Playwright browser tests | Node.js workspace `web/` |

Từ repository root:

```bash
uv run --project backend pytest -q
uv run --project voice/server pytest -q tests/voice tests/scripts tests/ops
uv run --project talk/server pytest -q talk/server/tests
npm test
cd web && npm run lint && npm run build
```

Không chạy `python -m pytest` chung từ root rồi coi đó là xác nhận toàn bộ
project: mỗi Python service có venv/dependencies riêng. Chạy e2e với:

```bash
npm run test:e2e
```

Các port test cho browser phải đang rảnh. Scenario data và kết quả evaluation
được lưu trong `evals/`.
