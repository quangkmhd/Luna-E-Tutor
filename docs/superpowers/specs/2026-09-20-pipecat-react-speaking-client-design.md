# Pipecat React client cho phòng luyện nói

Ngày: 2026-09-20. Trạng thái: chờ người dùng duyệt đặc tả.

## 1. Mục tiêu

Thay lớp voice frontend tự viết bằng API React chính thức của Pipecat, đồng thời giữ nguyên giao diện và nghiệp vụ phòng luyện nói. Thành công nghĩa là vòng đời kết nối, phát bot audio, trạng thái microphone và sự kiện RTVI do Pipecat quản lý; ứng dụng chỉ chuyển các sự kiện transcript/output thành bubble hội thoại và đồng bộ trạng thái học tập đã lưu ở backend.

## 2. Nguồn chuẩn

Pipecat Context Hub được truy vấn trước khi thiết kế. Ví dụ chính thức dùng `PipecatClientProvider`, `PipecatClientAudio`, `usePipecatClient`, các hook trạng thái/media và `useRTVIClientEvent`. Tài liệu media management chỉ dẫn đặt `PipecatClientAudio` bên trong provider để component này tự tạo audio ẩn, gắn remote bot track và xử lý autoplay.

Không giữ một wrapper riêng mô phỏng các chức năng này. Phiên bản `@pipecat-ai/client-react` phải tương thích với `@pipecat-ai/client-js` đang dùng; lockfile là nguồn xác nhận phiên bản cài thực tế.

## 3. Phạm vi xóa và giữ

Xóa:

- `web/src/lib/speaking-voice.ts` và test riêng của wrapper này.
- Việc tự tạo `HTMLAudioElement`, tự gắn `MediaStream`, tự gọi `play()` và tự xử lý remote track.
- Timer polling trạng thái hội thoại.
- State machine kết nối/micro tự sao chép trạng thái của Pipecat.
- Callback constructor truyền tay qua nhiều lớp để mô phỏng event subscription.

Giữ:

- Giao diện `/speaking`, bố cục bubble, lựa chọn chủ đề/từ và tổng kết.
- REST API speaking cho lịch sử bền, bằng chứng từ vựng, level và trạng thái phiên.
- `SmallWebRTCTransport` và endpoint voice hiện tại.
- Soniox STT/TTS trong pipeline server Pipecat.
- Một lần đồng bộ REST sau khi Pipecat báo bot output đã hoàn thành; đây là đồng bộ dữ liệu học tập, không phải polling media.

## 4. Kiến trúc component

Một boundary client-only của phòng speaking tạo đúng một `PipecatClient` với `SmallWebRTCTransport`, rồi cung cấp nó qua `PipecatClientProvider`. `PipecatClientAudio` nằm trực tiếp trong provider và là nơi duy nhất phát bot audio.

`VoiceControls` trở thành component tiêu thụ context Pipecat:

- Lấy client bằng `usePipecatClient`.
- Lấy trạng thái transport bằng hook chính thức thay vì state `off/connecting/on` tự quản lý.
- Điều khiển microphone bằng hook mic chính thức.
- Gọi `startBotAndConnect` với endpoint và `speaking_session_id` khi người dùng bật voice.
- Gọi `disconnect` khi người dùng tắt hoặc component bị tháo.

Một bridge hội thoại dùng `useRTVIClientEvent`:

- `RTVIEvent.UserTranscript` cập nhật duy nhất một learner live bubble.
- `RTVIEvent.BotOutput` cập nhật duy nhất một Luna live bubble.
- Khi bot output có `spoken_status=completed`, gọi một lần `onRefresh` để lấy state học tập đã lưu. Chỉ xóa live bubble sau khi refresh thành công.

Business component `SpeakingRoom` không biết media track, audio element hoặc transport internals. Nó chỉ nhận text live và state bền.

## 5. Luồng dữ liệu

1. Người dùng bật voice.
2. Provider/client Pipecat khởi tạo thiết bị và kết nối SmallWebRTC.
3. `PipecatClientAudio` phát remote bot track.
4. Soniox transcript đi qua RTVI `UserTranscript`; UI thay nội dung một learner live bubble, không thêm bubble cho mỗi partial.
5. Server tạo `LLMTextFrame`, Soniox TTS phát âm thanh và RTVI phát `BotOutput`; UI thay nội dung một Luna live bubble.
6. Khi `BotOutput` hoàn tất, web tải state speaking một lần. Message bền thay live bubble mà không tạo khoảng trống hoặc bản sao.
7. Disconnect dọn tài nguyên qua client/provider Pipecat.

Không có interval, không suy đoán TTS từ REST, không phát track bằng code ứng dụng.

## 6. Lỗi và trạng thái

- Lỗi kết nối hiển thị chi tiết hữu ích và vẫn cho phép nhập văn bản.
- Autoplay bị chặn được xử lý theo API/component Pipecat chính thức, không tạo audio element thứ hai.
- Refresh backend thất bại giữ live Luna bubble và hiển thị lỗi đồng bộ; không làm câu vừa nói biến mất.
- Partial transcript rỗng không tạo bubble.
- Event đến sau disconnect không được cập nhật vào phiên đã đóng.
- Provider chỉ được tạo lại khi session ID thay đổi có chủ ý.

## 7. Kiểm thử và tiêu chí chấp nhận

1. Test provider tạo một client cho một speaking session và gửi đúng request body.
2. Test `PipecatClientAudio` được mount trong provider; code ứng dụng không tạo `Audio` hoặc `MediaStream`.
3. Test transport state quyết định chính xác nhãn và trạng thái nút voice.
4. Test partial/final `UserTranscript` chỉ tạo một learner live bubble.
5. Test `BotOutput` đang chạy và hoàn tất chỉ tạo một Luna live bubble.
6. Test không gọi REST refresh từ user transcript hoặc timer; chỉ gọi một lần khi bot output hoàn tất.
7. Test refresh lỗi không xóa Luna live bubble.
8. Test disconnect/unmount dọn kết nối.
9. Toàn bộ Vitest, ESLint và Next.js production build phải qua.
10. Kiểm tra live bằng một phiên voice mới: không vang do nhiều audio player, không mất/reappearing bubble, không nhân đôi câu.

## 8. Ngoài phạm vi

- Không thay đổi pipeline Soniox/Pipecat server trong refactor frontend này.
- Không thay đổi giao diện hoặc thiết kế bài học.
- Không đưa Pipecat UI block library vào nếu React SDK cơ bản đã đáp ứng nhu cầu.
- Không xóa REST state vì đó là nguồn dữ liệu học tập bền, khác với media/session lifecycle của Pipecat.
