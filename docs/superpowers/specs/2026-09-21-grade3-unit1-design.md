# Lớp 3 Unit 1 “Hello” trong Luna

Ngày: 2026-09-21. Trạng thái: chờ duyệt đặc tả để lập kế hoạch triển khai.

## Mục tiêu và phạm vi

Thêm `grade03.unit01` để học sinh học trọn bài “Hello” qua Lesson 1–3, Level 2, Level 3, Free Talk trong bài và tổng kết. Cả nhập chữ và Pipecat voice phải chạy qua cùng Teaching Engine, lưu phiên và bằng chứng học tập như các Unit lớp 5. Màn chọn bài phải phân biệt lớp và Unit rõ ràng. Giữ nguyên nội dung và phiên đã lưu của lớp 5.

Nguồn nội dung là `docs/Global_Success_Khung_Nghe_Noi_3_Level_v3.xlsx`, sheet `Lớp 3 (3 Level)`, hàng 2–4, Unit 1 “Hello”. Nội dung dạy và ví dụ phải truy vết về ô nguồn. Importer chỉ trích xuất và kiểm toán mục tiêu; người biên soạn viết hoạt động, tiêu chí hoàn thành và hỗ trợ học sinh.

## Học liệu và luồng dạy

Tạo `curriculum/grade-03/unit-01/` theo hợp đồng manifest hiện hành: `unit.yaml`, ba Lesson, hai Level, Free Talk. Thứ tự stage là warm-up → lesson-01 → lesson-02 → lesson-03 → level-02 → level-03 → free-talk → summary. Warm-up chỉ chào, hỏi cảm xúc và dẫn vào bài; không dạy trước từ mới. Mỗi hoạt động có lời mời học sinh phản hồi, tối đa hai lần thử theo completion rule hiện có. Đánh giá tách bằng chứng hiểu nghĩa, dùng từ và dùng mẫu câu; chỉ nhắc lại không được tính là sử dụng độc lập.

Lesson 1 lấy `hello`, `hi` và các mẫu giới thiệu tên ở D2/E2. Lesson 2 lấy `goodbye`, `bye`, `how are you`, `fine`, `thank you` và mẫu hỏi thăm/tạm biệt ở D3/E3. Lesson 3 ôn lại Lesson 1–2 và thực hành âm /h/, /b/ theo C4; không biến dòng “Ôn tập” ở D4/E4 thành mục tiêu mới. Level 2 lấy F2/G2; Level 3 lấy H2/I2. Chuỗi `numbers 20–100` phải được biểu diễn như phạm vi số, không tự tạo hàng chục từ riêng. Free Talk dùng J2 làm bối cảnh hội thoại, lồng một mục tiêu ôn tập khi phù hợp và kết thúc theo yêu cầu học sinh. Câu hỏi về tên, tuổi, quê quán hoặc gia đình không đòi thông tin cá nhân thật; chấp nhận nhân vật giả và tránh suy đoán dữ kiện của học sinh.

## Định tuyến và giao diện

Registry đưa `grade03.unit01` vào cùng danh sách Unit hiện có và trả metadata `grade`, `unit`, `title`. Chọn Unit và tạo phiên vẫn dùng ID đầy đủ. Màn chọn nhóm bài theo lớp, không còn nhãn cố định “Grade 5 English”. Đường dẫn lớp 5 `/unit1`–`/unit5` tiếp tục hoạt động. Lớp 3 Unit 1 có đường dẫn `/grade3/unit1` hoặc slug tương đương không trùng; hàm tạo đường dẫn nhận đủ grade và unit, không chỉ số Unit. Trang học và tiêu đề phiên hiển thị lớp, Unit và tên bài từ metadata. Chọn bài khác hoặc tạo phiên mới giữ đúng ID đã chọn.

## System prompt theo lớp

Mỗi lớp đang hoạt động có system prompt Teacher và Evaluator riêng dưới `backend/src/luna_tutor/prompts/grades/grade-03/` và `grade-05/`. Quy tắc bất biến về quyền hạn của Engine, ranh giới dữ liệu không đáng tin, quyền riêng tư, cấu trúc output và cách đọc bằng chứng nằm trong tệp chung. Bộ nạp prompt nhận `grade: int` và vai trò `teacher | evaluator`, xác nhận cặp tệp tồn tại và nội dung không rỗng, rồi ghép phần chung với phần riêng thành đúng một system message. Không tự dùng prompt lớp 5 khi thiếu lớp khác; lỗi cấu hình phải nêu rõ grade/role. Chỉ cần tạo thư mục cho lớp 3 và lớp 5 hiện có; cấu trúc cho phép thêm lớp 1, 2, 4 sau này.

Prompt lớp 3 điều chỉnh độ dài câu, nhịp và ví dụ cho người học lớp 3, ưu tiên chào hỏi và tương tác ngắn. Prompt lớp 5 giữ hành vi đang có. Giữ danh tính học sinh Quang theo cấu hình hiện tại, nhưng bỏ giả định Quang luôn học lớp 5. Ví dụ chỉ hướng dẫn cách đáp lời, không làm Luna chuyển sang từ vựng Unit khác. Description catalog là quy tắc chung; nội dung phụ thuộc Unit nằm trong curriculum, không chôn trong prompt dùng chung. `JevEvaluator` dùng rubric có cấu trúc chung và nhận cùng metadata lớp/Unit ở nhánh so sánh, để hai evaluator xét cùng học liệu.

Runtime tạo Teacher/Evaluator theo grade và tái sử dụng cho các Unit cùng lớp; UnitTurnRouter vẫn định tuyến theo ID Unit đầy đủ. Review so sánh dùng đúng prompt lớp của phiên. Các request text/voice phải nhận cùng cấu hình system prompt từ curriculum đã xác nhận.

## Voice và chỗ ghi cứng

Voice STT context hiện cố định “Grade 5 Unit 1 All about me”; tạo context từ Unit đang học để Soniox nhận đúng từ và mẫu câu. Voice session phải kiểm tra ID và lấy đúng curriculum trước khi dựng STT/worker. Các luồng review/eval phải định tuyến theo ID đầy đủ, đồng thời giữ default lớp 5 nếu người gọi không chỉ định Unit.

Chỉ thay các giá trị ghi cứng ảnh hưởng đến trải nghiệm đa lớp. Tài liệu lịch sử, fixture/test lớp 5, và màn nguyên tắc thiết kế riêng lớp 5 vẫn có thể gọi tên lớp 5 khi đó là nội dung chủ đích.

## Lỗi và tương thích

ID Unit không tồn tại bị từ chối rõ ràng; không tự chuyển sang lớp 5. Phiên cũ `grade05.*` tiếp tục đọc và chạy với curriculum tương ứng. Nếu học liệu lớp 3 thiếu reference, thiếu hoạt động bao phủ mục tiêu, hoặc sai thứ tự stage thì registry không khởi động. Voice không được gợi ý từ vựng của Unit khác.

## Kiểm chứng

- Kiểm toán workbook hàng 2–4 với tập từ/mẫu câu đã biên soạn; kiểm tra Lesson 3 chỉ ôn và các ô Level 2–3 không trôi sang Unit khác.
- Load/validate toàn bộ curriculum lớp 3 và lớp 5; kiểm tra registry, API `/api/units`, tạo/đọc/reset/finish phiên theo ID đầy đủ.
- Kiểm tra cả hai lớp nạp đúng cặp Teacher/Evaluator system prompt, cùng Unit khác nhau trong một lớp dùng đúng prompt lớp đó; thiếu grade/role báo lỗi thay vì dùng lớp 5. Kiểm tra review so sánh giữ đúng grade.
- Chạy bài học text lớp 3 qua từng stage, bao gồm đúng, sai, im lặng, câu ngắn, tiếng Việt, hỏi cô và Free Talk; xác nhận không xuất hiện mục tiêu lớp 5.
- Kiểm tra voice worker nhận đúng Unit và STT context; chạy smoke voice thực tế khi có dịch vụ và khóa hiện hữu.
- Kiểm tra màn chọn và URL cho cả hai lớp, làm mới trang, tạo phiên mới, quay lại chọn bài; chạy hồi quy lớp 5.
