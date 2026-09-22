# Web — Luna English Tutor

Next.js frontend cho lớp học theo Unit và trang Free Talk. Đây là một trong bốn
service của repository; xem [README root](../README.md) để biết toàn bộ kiến trúc.

## Kết nối service

| Biến khi khởi động | Mặc định local | Service đích |
| --- | --- | --- |
| `NEXT_PUBLIC_TUTOR_API_URL` | để trống (`/api` cùng cổng web) | backend FastAPI qua Next.js proxy |
| `NEXT_PUBLIC_PIPECAT_URL` | `http://localhost:7860` | voice Pipecat |
| `NEXT_PUBLIC_TALK_PIPECAT_URL` | `http://localhost:7863` | talk Pipecat |

Đây là biến `NEXT_PUBLIC_*`: URL được đưa vào bundle trình duyệt khi Next.js
khởi động. Dừng và chạy lại web sau khi thay đổi chúng. Proxy `/api` mặc định
trỏ tới `127.0.0.1:8000`; khi triển khai có thể đặt `VPS_HOST` và
`BACKEND_PORT` để đổi backend đích.

## Chạy local

Từ thư mục này, sau khi backend, voice và talk đã chạy:

```bash
npm install
NEXT_PUBLIC_PIPECAT_URL=http://localhost:7860 \
NEXT_PUBLIC_TALK_PIPECAT_URL=http://localhost:7863 \
  npm run dev
```

Mở http://localhost:3000 cho lớp học theo Unit hoặc http://localhost:3000/talk
cho Free Talk. Để chạy cả bốn service bằng một lệnh, dùng từ repository root:

```bash
./scripts/run-local.sh
```

## Scripts

```bash
npm run dev       # development server
npm run lint      # ESLint
npm test          # Vitest
npm run build     # production build
npm run test:e2e  # Playwright
```

`npm run test:e2e` dùng các port test riêng; xem [tests/README.md](../tests/README.md).

## Cấu trúc

```text
web/
├── src/app/          # Next.js routes, gồm /talk
├── src/components/   # UI components
├── src/lib/          # API client và helpers
└── package.json      # scripts và dependencies
```

Không lưu API key trong web hoặc trong biến `NEXT_PUBLIC_*`; các khóa provider
chỉ nằm trong `.env` ở root và được Python services sử dụng.
