# Kết quả quan trọng từ lượt chạy Evaluator thật

**Ngày chạy:** 2026-09-23  
**Evaluator:** Jev qua OpenRouter (`~typesafe/jev-latest`)  
**Số câu mẫu:** 16  
**Dữ liệu JSON đầy đủ:** [evaluator-live-outputs-2026-09-23.json](evaluator-live-outputs-2026-09-23.json)

## Hành vi đã được xác nhận

| Tình huống | Lời học sinh | Kết quả Evaluator |
|---|---|---|
| Trả lời đúng | “I live in the countryside.” | `answer`; nghĩa `satisfied`; cấu trúc `correct_target_form` |
| Trả lời ngắn nhưng đủ ý | “Countryside.” | `answer`; nghĩa `satisfied`; không bị coi là lỗi vì thiếu câu đầy đủ |
| Sai ngữ pháp nhưng rõ ý | “I live countryside.” | Nghĩa `satisfied`; cấu trúc `error_in_target_form`; `recast_needed: true` |
| Nhắc lại từ mẫu | “City.” khi được mời nói “city” | `correct_target_form`; nghĩa `not_demonstrated` — bắt chước không bị tính nhầm là hiểu nghĩa |

## Các điểm cần xử lý

### 1. Sai loại đáp án bị phân loại thành lạc chủ đề

**Đầu vào:** Luna hỏi “What is your favourite animal?”; học sinh đáp “Pink.”  
**Đầu ra:** `meaning_status: wrong_semantic_category`, nhưng `response_kind: off_topic`.

Hai nhãn này không thống nhất. Đây là câu trả lời cho câu hỏi nhưng sai loại ý nghĩa; cần để Evaluator trả `response_kind: answer` cùng `wrong_semantic_category`.

### 2. Yêu cầu cô nói chậm bị đánh dấu cần làm rõ

**Đầu vào:** “Can you speak more slowly?”  
**Đầu ra:** `response_kind: asks_teacher`, nhưng `needs_clarification: true`.

Câu nói rõ ràng và đã được nhận diện là góp ý cho cô, nên không nên yêu cầu học sinh làm rõ.

### 3. Từ chối trả lời bị gộp vào “không biết”

**Đầu vào:** “I don't want to answer.”  
**Đầu ra:** `response_kind: does_not_know`.

Schema hiện chưa có nhãn riêng cho việc không muốn trả lời. Vì vậy Engine khó chọn phản hồi tôn trọng lời từ chối khác với hỗ trợ học sinh chưa biết đáp án.

### 4. Hỏi nghĩa từ nhưng vẫn bị ghi nhận dùng đúng từ mục tiêu

**Đầu vào:** Luna mời nói “city”; học sinh hỏi “What does city mean?”  
**Đầu ra:** `response_kind: asks_meaning`, nhưng `target_form_status: correct_target_form`.

Câu hỏi nghĩa không phải lượt nói từ vựng theo yêu cầu. Cần tránh tính từ mục tiêu xuất hiện trong câu hỏi như bằng chứng học sinh đã nói đúng từ.

### 5. Câu trả lời đúng một phần nhưng bị yêu cầu làm rõ

**Đầu vào:** transcript cuối lượt “I live...”  
**Đầu ra:** `meaning_status: partially_satisfied`, `needs_clarification: true`.

Cần thống nhất cách xử lý giữa “câu trả lời thiếu thông tin” và “transcript không đáng tin cậy”. Nếu transcript đáng tin nhưng câu trả lời chưa hoàn chỉnh, thường nên ghi nhận phần đã có và để Teaching Engine hỏi phần còn thiếu.

## Những trường hợp không được gọi qua LLM

- **Im lặng/không có phản hồi:** được hệ thống tạo thành sự kiện nội bộ `no_response`; không có kết quả LLM cho trường hợp này.
- **Thông tin liên hệ nhạy cảm:** được lọc trước khi gọi Evaluator; cần kiểm tra ở lớp riêng tư, không dùng kết quả LLM để kết luận.
- **Lượt thử thứ hai:** Evaluator trả cùng loại bằng chứng như lượt đầu. Bộ đếm lượt thử thuộc trách nhiệm của Teaching Engine, không phải nhãn bằng chứng của Evaluator.

## Giới hạn của kết quả

Đây là một lượt chạy thật cho mỗi câu mẫu. Kết quả giúp phát hiện điểm cần sửa trong rubric/schema, nhưng chưa đo độ ổn định của model qua nhiều lần chạy.
