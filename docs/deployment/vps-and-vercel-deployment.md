# Hướng dẫn Triển khai: VPS (Docker) & Vercel (Frontend)

Tài liệu này hướng dẫn chi tiết cách triển khai hệ thống **Luna English Tutor** theo mô hình tối ưu:
- **Máy chủ VPS**: Chạy `backend` (FastAPI + SQLite), 2 Pipecat Voice Bots (`voice` & `talk`) và `nginx` bằng Docker Compose.
- **Vercel**: Chạy giao diện người dùng `web` (Next.js 16 + React 19).

---

## Kiến trúc hệ thống

```
                               ┌────────────────────────────────────────┐
                               │             NGƯỜI DÙNG                 │
                               │      (Trình duyệt / Điện thoại)        │
                               └──────────────────┬─────────────────────┘
                                                  │
                  ┌───────────────────────────────┴───────────────────────────────┐
                  │ (1) Truy cập Web (HTTPS)                                      │ (2) API REST & WebRTC Audio (HTTPS/WSS)
                  ▼                                                               ▼
   ┌──────────────────────────────┐                              ┌──────────────────────────────────┐
   │       VERCEL (FRONTEND)      │                              │            MÁY CHỦ VPS           │
   │  Next.js 16 (Static + Edge)  │                              │       (Docker Compose Stack)     │
   │                              │                              │                                  │
   │  Biến môi trường:            │                              │   ┌──────────────────────────┐   │
   │  - NEXT_PUBLIC_TUTOR_API_URL ┼─────────────────────────────►│   │  Nginx Reverse Proxy     │   │
   │  - NEXT_PUBLIC_PIPECAT_URL   │                              │   │  (Port 80 / 443 + SSL)   │   │
   │  - NEXT_PUBLIC_TALK_...      │                              │   └──┬─────────┬─────────┬───┘   │
   └──────────────────────────────┘                              │      │         │         │       │
                                                                 │      ▼         ▼         ▼       │
                                                                 │  [backend]  [voice]   [talk]     │
                                                                 │   (:8000)   (:7860)   (:7863)    │
                                                                 └──────────────────────────────────┘
```

> [!IMPORTANT]
> **Yêu cầu Bắt buộc về HTTPS / SSL:**
> - Frontend chạy trên Vercel luôn có HTTPS (`https://*.vercel.app`).
> - Trình duyệt sẽ **chặn hoàn toàn** (Mixed Content error) nếu trang HTTPS gọi đến một API hoặc WebRTC chạy `http://` không bảo mật.
> - Đồng thời, các trình duyệt hiện đại (Chrome, Safari, iOS, Android) **chỉ cấp quyền truy cập Microphone khi trang web chạy qua HTTPS**.
> - Do đó, máy chủ VPS **phải có tên miền và chứng chỉ SSL** (bạn có thể dùng Let's Encrypt miễn phí hoặc Cloudflare Tunnel).

---

## PHẦN 1: Triển khai Backend & Voice trên VPS (Docker)

### Bước 1: Chuẩn bị máy chủ VPS
Cài đặt Docker và Docker Compose trên VPS (ví dụ Ubuntu 22.04 / 24.04):

```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài đặt Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Cài đặt Docker Compose plugin
sudo apt install -y docker-compose-plugin

# Phân quyền cho user hiện tại (không cần gõ sudo mỗi lần chạy docker)
sudo usermod -aG docker $USER
newgrp docker
```

### Bước 2: Đưa mã nguồn lên VPS
Bạn có thể dùng `git clone` hoặc dùng `rsync` / `scp` đẩy code từ máy local lên VPS:

```bash
# Cách 1: Clone qua Git (khuyên dùng)
git clone <URL_REPO_CUA_BAN>
cd E-Voice-Tutor-v1

# Cách 2: Hoặc rsync từ máy local lên VPS
# rsync -avz --exclude='.git' --exclude='.venv' --exclude='node_modules' ./ user@<IP_VPS>:~/E-Voice-Tutor-v1/
```

### Bước 3: Cấu hình file `.env` trên VPS
Tạo file `.env` tại thư mục gốc của project trên VPS:

```bash
cp .env.example .env
nano .env
```

Điền các thông tin API keys thật:
```dotenv
# API Keys bắt buộc cho Tutor bài học (Units 1-5)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=google/gemini-3.5-flash-lite
TUTOR_EVALUATOR_MODEL=~typesafe/jev-latest

SONIOX_API_KEY=snx_proj_xxxxxxxxxxxxxxxxxxxxx
SONIOX_VOICE_ID=Grace
SONIOX_TTS_VOICE=Grace
STT_PROVIDER=soniox

# Database path (đã cấu hình sẵn cho Docker volume)
TUTOR_DATABASE_PATH=/app/backend/data/luna-tutor.sqlite3

# API Key cho phòng Free Talk tự do (nếu dùng)
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxx
TALK_LLM_MODEL=gemini-3.5-flash-lite

# CORS: Cho phép domain Vercel gọi vào (hoặc để * nếu mở cho mọi domain)
ALLOWED_ORIGINS=*
PIPECAT_ALLOWED_ORIGINS=*

# STUN server cho WebRTC kết nối xuyên qua NAT/Firewall
PIPECAT_ICE_SERVERS=stun:stun.l.google.com:19302
```

### Bước 4: Khởi động hệ thống với Docker Compose
Trên VPS, chạy lệnh:

```bash
# Build và chạy ngầm tất cả các container (backend, voice, talk, nginx)
docker compose up -d --build
```

Kiểm tra trạng thái các container:
```bash
docker compose ps
```
Kết quả mong muốn:
- `luna-backend`: Up (cổng 8000)
- `luna-voice`: Up (cổng 7860)
- `luna-talk`: Up (cổng 7863)
- `luna-nginx`: Up (cổng 80)

Xem logs thời gian thực khi cần debug:
```bash
docker compose logs -f
# hoặc xem riêng từng service:
# docker compose logs -f backend
# docker compose logs -f voice
```

### Bước 5: Cấu hình Tên miền & SSL (HTTPS) cho VPS

Để Vercel gọi được vào VPS và trình duyệt mở được Micro, bạn cần gắn domain và SSL cho VPS. Có 2 cách đơn giản nhất:

#### Cách A: Dùng Cloudflare Tunnel (Nhanh nhất, Không cần mở port, Miễn phí SSL)
1. Đăng ký tài khoản [Cloudflare](https://dash.cloudflare.com) và trỏ domain về Cloudflare.
2. Cài đặt `cloudflared` trên VPS:
   ```bash
   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared.deb
   ```
3. Tạo tunnel trỏ về Nginx (cổng 80):
   - Đặt public hostname: ví dụ `api-tutor.yourdomain.com` ➡️ HTTP `localhost:80`.
   - Cloudflare sẽ tự động cấp SSL HTTPS chuẩn: `https://api-tutor.yourdomain.com`.

#### Cách B: Dùng Certbot (Let's Encrypt) trực tiếp trên VPS
1. Trỏ bản ghi DNS `A` của domain (ví dụ `api.yourdomain.com`) về địa chỉ IP của VPS.
2. Mở cổng 80 và 443 trên tường lửa VPS:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```
3. Dùng Certbot tạo chứng chỉ SSL và cấu hình SSL trong Nginx.

---

## PHẦN 2: Triển khai Frontend lên Vercel

### Bước 1: Đẩy code lên GitHub / GitLab
Đảm bảo bạn đã push code của repository lên GitHub.

### Bước 2: Import dự án vào Vercel
1. Đăng nhập vào [Vercel Dashboard](https://vercel.com).
2. Bấm **Add New...** ➡️ **Project**.
3. Chọn kho lưu trữ chứa code `E-Voice-Tutor-v1`.

### Bước 3: Cấu hình Build & Root Directory trên Vercel
- **Framework Preset**: Chọn `Next.js`.
- **Root Directory**: Bấm `Edit` và chọn thư mục **`web`** (rất quan trọng!).
- **Build Command**: Để mặc định (`next build`).
- **Output Directory**: Để mặc định (`.next`).

### Bước 4: Thêm Biến môi trường (Environment Variables)
Trong mục **Environment Variables** trên Vercel, thêm 3 biến sau:

| Tên biến | Giá trị mẫu (Thay bằng domain VPS có HTTPS của bạn) |
|---|---|
| `NEXT_PUBLIC_TUTOR_API_URL` | `https://api-tutor.yourdomain.com/api` (hoặc `https://api.yourdomain.com:8000`) |
| `NEXT_PUBLIC_PIPECAT_URL` | `https://api-tutor.yourdomain.com/voice` (hoặc `https://api.yourdomain.com:7860`) |
| `NEXT_PUBLIC_TALK_PIPECAT_URL` | `https://api-tutor.yourdomain.com/talk` (hoặc `https://api.yourdomain.com:7863`) |

> [!TIP]
> Nếu bạn dùng Nginx reverse proxy đi kèm với đường dẫn prefix:
> - `NEXT_PUBLIC_TUTOR_API_URL=https://api-tutor.yourdomain.com` (Nginx tự chuyển tiếp các request `/api/*` tới backend)
> - `NEXT_PUBLIC_PIPECAT_URL=https://api-tutor.yourdomain.com/voice`
> - `NEXT_PUBLIC_TALK_PIPECAT_URL=https://api-tutor.yourdomain.com/talk`

### Bước 5: Bấm Deploy
1. Bấm nút **Deploy**.
2. Chờ 1–2 phút để Vercel build xong.
3. Sau khi hoàn tất, Vercel sẽ cấp link truy cập dạng `https://ten-du-an.vercel.app`.

---

## PHẦN 3: Kiểm tra hoạt động (Verification)

1. Mở trang web Vercel trên trình duyệt.
2. Trình duyệt sẽ hỏi quyền truy cập Microphone: Chọn **Allow** (Cho phép).
3. Chọn một Unit (ví dụ **Unit 1: All about me**) và bấm **Start Lesson**:
   - Kiểm tra xem bot có chào bằng giọng nói không.
   - Nói câu trả lời tiếng Anh vào micro và quan sát bot phản hồi.
4. Chuyển sang phòng **Free Talk** (`/talk`):
   - Chọn chủ đề và kiểm tra cuộc hội thoại tự do.
5. Kiểm tra file cơ sở dữ liệu trên VPS:
   ```bash
   # Dữ liệu học sinh được lưu bền vững tại:
   ls -la backend/data/luna-tutor.sqlite3
   ```
   Dữ liệu này được mount ra ngoài ổ cứng của VPS, nên ngay cả khi restart hay cập nhật Docker container, tiến trình học và lịch sử đều không bị mất.

---

## Các lệnh bảo trì thường dùng trên VPS

```bash
# Cập nhật code mới trên VPS
git pull
docker compose up -d --build

# Khởi động lại toàn bộ
docker compose restart

# Dừng hệ thống
docker compose down

# Xem dung lượng RAM/CPU các container
docker stats
```
