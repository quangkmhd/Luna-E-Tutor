# Viết một lesson lớp 3

Mỗi `lesson-XX/content.yaml` có một lời chào và ba trạm theo thứ tự `vocabulary`, `patterns`, `conversation`. Tạo thư mục `lesson-02`, `lesson-03`… và viết `content.yaml` theo mẫu dưới đây. Hệ thống tự tìm file lesson mới khi khởi động; không cần thêm file vào `unit.yaml`.

```yaml
lesson: 2
title: Hỏi thăm sức khỏe
greeting:
  order: 1
  say: "Hi, con! Hôm nay cô trò mình hỏi thăm nhau nhé."
  accept: Con đáp lại bằng Hi hoặc Hello; một câu chào ngắn cũng đạt.
words: [how, you, fine, thank you]
patterns:
  ask: "How are you?"
  answer: "Fine, thank you."
stations:
- id: vocabulary
  steps:
  - order: 2
    target: how
    say: |-
      [long pause] "HOW" [long pause] dùng để hỏi như thế nào.
      Listen first! [long pause] "HOW" [long pause]
      Your turn now! Can you say: [long pause] "How" [long pause]?
    accept: Chấp nhận con nói “how”; chưa cần dùng trong câu.
- id: patterns
  steps:
  - order: 3
    target: ask
    say: 'Listen first! [long pause] "How are you?" [long pause] Now you ask me!'
    accept: Chấp nhận “How are you?” hoặc câu hỏi thăm tương đương.
- id: conversation
  steps:
  - order: 4
    target: answer
    say: "How are you today?"
    accept: Chấp nhận “Fine”, “I'm fine”, hoặc câu nói cảm xúc thật phù hợp.
```

- `order` đếm **mục dạy** liên tục cho toàn lesson: chào là 1, mục đầu trạm 1 là 2. Không đánh số câu học sinh. Cô chào rồi chờ con đáp theo `greeting.accept` trước khi vào Trạm 1.
- `say` là lời cô nói. Khi cô đọc mẫu một từ hoặc câu, đặt mẫu trong dấu ngoặc kép và kẹp hai bên bằng `[long pause]`, ví dụ `[long pause] "Hello" [long pause]`.
- `accept` là mô tả cho LLM đánh giá câu con vừa nói. Ghi rõ cách nói thiếu hoặc sai nhẹ vẫn được chấp nhận. Nội dung này không được phát cho học sinh.
- `target` dùng từ trong `words` hoặc khóa trong `patterns`. Có thể bỏ qua ở trò chơi hay hội thoại không kiểm tra một từ/mẫu câu riêng.
- Nếu cùng một mục cần thêm lượt cô nói và con đáp, thêm `more`:

```yaml
    more:
    - say: 'Once more! [long pause] "How" [long pause]'
      accept: Con nói “how”.
```

Lời cô sau lượt học sinh cũng đặt trong `more` với `say` và không có `accept`. Khi con đạt, cô nói đúng `say` tiếp theo. Khi con chưa đạt, cô đưa mẫu hoặc gợi ý ngắn cho mục hiện tại, không đọc lại toàn bộ lời giới thiệu. Mặc định một mục cho con tối đa 2 lần trả lời; hết lượt mà chưa đạt, cô dùng câu `say` của mục cũ, câu con vừa nói và lịch sử chat để sửa câu cũ bằng một câu trần thuật, không mời con đọc lại, rồi đọc đúng `say` tiếp theo. Nếu cần số lượt khác, thêm `attempts: 1` (từ 1 đến 5) ngay dưới `order`. Các trường nội bộ như objective ID, stage ID và luật chuyển trạm được quản lý bởi code.

Lời khen phụ thuộc vào bằng chứng, nhất là câu khẳng định đã nghe rõ một âm, không đặt thành câu cố định nếu hệ thống chỉ có bản chép lời. Teacher tạo lời hỗ trợ khi câu trả lời chưa đạt hoặc con hỏi thêm.
