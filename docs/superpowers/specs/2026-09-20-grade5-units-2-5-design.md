# Thiết kế mở rộng Luna lớp 5 — Unit 2 đến Unit 5

Ngày: 2026-09-20. Trạng thái: thiết kế đã được thống nhất trong hội thoại; chờ người dùng duyệt bản spec trước khi lập kế hoạch triển khai.

## 1. Mục tiêu

Mở rộng ứng dụng Luna từ một curriculum cố định là Grade 5 Unit 1 thành ứng dụng có thể chọn và chạy đầy đủ Grade 5 Unit 1–5. Unit 2–5 phải giữ cùng hợp đồng sư phạm và cùng luồng text/voice như Unit 1, nhưng nội dung, mục tiêu, hoạt động và Free Talk phải lấy đúng từ workbook nguồn thay vì sao chép rồi thay từ khóa.

Các Unit mới:

| Unit | Tiêu đề | Vùng nguồn |
| --- | --- | --- |
| 2 | Our homes | `Lớp 5 (3 Level)!A5:M7` |
| 3 | My foreign friends | `Lớp 5 (3 Level)!A8:M10` |
| 4 | Our free-time activities | `Lớp 5 (3 Level)!A11:M13` |
| 5 | My future job | `Lớp 5 (3 Level)!A14:M16` |

Nguồn chuẩn là `docs/Global_Success_Khung_Nghe_Noi_3_Level_v3.xlsx`. Nội dung đã commit phải truy vết được về đúng ô nguồn. Nếu workbook và curriculum khác nhau, kiểm thử phải báo rõ chỗ khác thay vì âm thầm chấp nhận.

Ngoài phạm vi:

- Không thêm Grade khác hoặc Unit 6 trở đi.
- Không thay đổi provider STT, TTS hoặc LLM.
- Không viết lại Teaching Engine đang hoạt động.
- Không tự động sinh hoạt động dạy rồi coi là đã được duyệt.
- Không yêu cầu hoặc lưu địa chỉ thật, thông tin liên hệ hay dữ liệu cá nhân của trẻ.

## 2. Ba hướng đã cân nhắc

### A. Sao chép Unit 1 bốn lần

Nhanh lúc đầu nhưng dễ giữ nhầm câu hỏi, ID, tiêu chí bằng chứng và Free Talk của Unit 1. Cách này cũng nhân bản các đường dẫn ghi cứng và khó phát hiện nội dung lấy sai ô. Không chọn.

### B. Registry đa-unit và curriculum được kiểm chứng từ nguồn

Tạo một registry nhỏ cho curriculum, làm cho session và TurnService định tuyến bằng `unit_id`, đồng thời biên soạn từng Unit từ dữ liệu đã trích và kiểm chứng. Nội dung chung vẫn nằm trong Engine/prompt chung; nội dung riêng nằm trong thư mục Unit. Đây là phương án được chọn vì tạo một seam rõ, giảm hard-code và cho phép kiểm thử chính xác từng Unit.

### C. Sinh toàn bộ curriculum và hoạt động trực tiếp từ Excel

Giảm công nhập liệu nhưng workbook chỉ chứa ngữ liệu và gợi ý, không chứa đủ completion rule, thứ tự hoạt động, tiêu chí bằng chứng hay nhánh hỗ trợ. Các ô như `numbers 23, 38, 93, 116` cũng chứng minh việc tách chuỗi chung có thể sai. Không chọn làm đường chạy sản phẩm. Importer chỉ hỗ trợ trích nguồn và kiểm toán.

## 3. Quy tắc lấy dữ liệu chính xác

### 3.1. Ý nghĩa từng cột

| Cột | Cách sử dụng |
| --- | --- |
| A | ID, tiêu đề Unit, trang SGK và phạm vi Unit |
| B | Lesson 1–3 và period |
| C | Trọng âm/phát âm chính thức của Lesson 3 |
| D | Từ vựng Level 1 theo Lesson |
| E | Mẫu câu Level 1 theo Lesson |
| F | Từ vựng mở rộng Level 2 ở phạm vi Unit |
| G | Mẫu câu mở rộng Level 2 ở phạm vi Unit |
| H | Từ vựng nâng cao Level 3 ở phạm vi Unit |
| I | Mẫu câu nâng cao Level 3 ở phạm vi Unit |
| J | Gợi ý hội thoại dùng để thiết kế Free Talk |
| K | Nguồn tham chiếu cho Level 3; không phải nội dung để Luna dạy |
| L | Trọng tâm phát âm và lỗi thường gặp; dùng làm hướng dẫn, không dùng transcript text để khẳng định trẻ phát âm đúng |
| M | Gợi ý khích lệ; chuyển thành hành vi linh hoạt, không đóng đinh một câu khen cố định |

Ô gộp chỉ được kế thừa khi anchor nằm trong cùng phạm vi Unit. Ô trống ở Lesson 2 hoặc 3 không được lấy dữ liệu từ Unit trước hoặc Unit sau. Lesson 3 tham chiếu mục tiêu Lesson 1–2; chuỗi “Ôn tập” không trở thành từ vựng mới.

### 3.2. Quy tắc chuẩn hóa

- Giữ nguyên văn bản gốc và tọa độ ô trong bằng chứng kiểm toán.
- Danh sách từ vựng thông thường tách theo dấu phẩy, dấu chấm phẩy hoặc xuống dòng.
- Cụm nhiều từ như `go for a walk`, `play the violin`, `traditional clothes`, `fire engine` là một target, không tách theo khoảng trắng.
- Mẫu câu Level 1 trong cùng ô tách theo dấu chấm phẩy hoặc xuống dòng; mẫu Level 2–3 tách theo xuống dòng. Dấu `/`, dấu nháy và ô trống `___` được giữ nguyên.
- `numbers 23, 38, 93, 116` ở Unit 2 Lesson 2 được chuẩn hóa thành bốn target `23`, `38`, `93`, `116`; từ `numbers` chỉ mô tả nhóm, không phải target thứ năm.
- `percussion/wind/string instruments` ở Unit 4 Level 3 phải được người biên soạn xem là ba nhóm có quan hệ, không để slash tạo một ID khó hiểu hoặc tự đổi nghĩa.
- Các dạng `A ___ ___s.` và câu điều kiện/mệnh đề quan hệ được giữ nguyên trong pattern; không tự sửa ngữ pháp nguồn trong bước import.
- ID phải ổn định, có namespace Unit và không phụ thuộc cách viết hoa. Mọi override chuẩn hóa phải có test và ghi chú lý do.

### 3.3. Kiểm toán nguồn

Importer tiếp tục là công cụ đọc nguồn, không phải activity generator. Kiểm thử theo bảng tham số cho Unit 1–5 sẽ:

1. đọc đúng sheet và phạm vi Unit;
2. xác nhận title, Lesson và tọa độ nguồn;
3. so sánh tập vocabulary/pattern đã chuẩn hóa với curriculum đã commit;
4. kiểm tra Lesson 3 chỉ review Lesson 1–2;
5. phát hiện target thiếu, target thừa hoặc target trôi sang Unit khác;
6. có regression riêng cho các ngoại lệ `numbers` và slash-group của Unit 4.

## 4. Curriculum của từng Unit

Mỗi thư mục `curriculum/grade-05/unit-0N/` giữ cùng cấu trúc nạp đã được Unit 1 kiểm chứng:

```text
unit.yaml
lesson-01/content.yaml
lesson-02/content.yaml
lesson-03/content.yaml
level-02/content.yaml
level-03/content.yaml
free-talk/content.yaml
```

Mỗi Unit có tám stage theo thứ tự:

```text
warm-up → lesson-01 → lesson-02 → lesson-03
        → level-02 → level-03 → free-talk → summary
```

Warm-up chỉ chào, kiểm tra cảm xúc và dẫn vào chủ đề; không dạy vocabulary. Mỗi từ/cụm từ mới có một hoạt động `vocabulary_introduction`: Luna diễn đạt lời khen hoặc cầu nối tự nhiên khi phù hợp, đọc target hai lần, mời trẻ nói, chờ phản hồi rồi mới chuyển tiếp. Không đọc cả danh sách trong một lượt.

Các hoạt động pattern phải có mục tiêu giao tiếp và tiêu chí bằng chứng riêng. Câu khác mẫu nhưng đúng nghĩa được ghi nhận là giao tiếp thành công; việc dùng đúng target form được ghi riêng. Lesson 3 ôn lại mục tiêu Level 1 và trọng âm/phát âm trong cột C/L mà không tạo objective từ vựng mới.

Level 2 dùng F/G; Level 3 dùng H/I. Free Talk dùng J làm ngữ cảnh chính, kết hợp các mục đang chờ ôn. Gợi ý ở M ảnh hưởng cách phản hồi nhưng không bắt Teacher nói đúng một câu mẫu. Nguồn K được giữ trong provenance hoặc tài liệu, không biến thành lời dạy.

### 4.1. Nội dung bắt buộc Unit 2

- Lesson 1: `building`, `flat`, `house`, `tower`; hỏi sống trong loại nhà nào.
- Lesson 2: `23`, `38`, `93`, `116`; luyện mẫu địa chỉ bằng dữ liệu giả.
- Level 2: `apartment`, `garden`, `neighbourhood`, `floor`; hỏi số tầng và apartment/house.
- Level 3: `underground`, `beam`, `mud`, `skylight`, `spring`, `fossil fuel`, `coal`; mô tả eco house.
- Phát âm: phân biệt trọng âm `fifteen/sixteen` với `fifty/sixty` theo nguồn.
- Quy tắc an toàn: Luna cung cấp địa chỉ nhân vật giả và không hỏi địa chỉ nhà thật của trẻ. Nếu trẻ tự nói thông tin cụ thể, hệ thống không lặp lại hoặc lưu nó vào bằng chứng học tập.

### 4.2. Nội dung bắt buộc Unit 3

- Lesson 1: `American`, `Australian`, `Japanese`, `Malaysian`; hỏi nationality.
- Lesson 2: `active`, `clever`, `friendly`, `helpful`; mô tả tính cách.
- Level 2: `British`, `Canadian`, `Chinese`, `Korean`, `Singaporean`, `Thai`; nơi đến và khả năng nói tiếng Anh.
- Level 3: `traditional clothes`, `samba parade`, `Chuseok`, `rice cakes`, `lucky money`, `celebration`; nói về lễ hội và bạn nước ngoài.
- Phát âm: giữ trọng âm âm tiết một của `active`, `friendly` khi đặt trong câu.
- Free Talk dùng nhân vật hư cấu; không yêu cầu trẻ khai thông tin nhận dạng của bạn thật.

### 4.3. Nội dung bắt buộc Unit 4

- Lesson 1: `go for a walk`, `play the violin`, `surf the Internet`, `water the flowers`; nói hoạt động yêu thích.
- Lesson 2: `always`, `often`, `sometimes`, `usually`; nói hoạt động cuối tuần.
- Level 2: `collect stamps`, `do puzzles`, `play board games`, `ride a bike`; mời tham gia và hỏi tần suất.
- Level 3: nhạc cụ, orchestra, nhóm nhạc cụ và các từ `hit`, `interact`, `amazed`; so sánh và nói cảm nhận về âm nhạc.
- Phát âm: trọng âm âm tiết một của `always`, `sometimes` và nhịp tự nhiên trong câu.
- Nội dung Internet chỉ hỏi về hoạt động ở mức chung, không xin tài khoản hoặc nền tảng cá nhân.

### 4.4. Nội dung bắt buộc Unit 5

- Lesson 1: `firefighter`, `gardener`, `reporter`, `writer`; nói nghề tương lai.
- Lesson 2: `grow flowers`, `report the news`, `teach children`, `write stories`; giải thích lý do chọn nghề.
- Level 2: `architect`, `designer`, `scientist`, `vet`; mô tả nghề và người thân trong tình huống hư cấu hoặc do trẻ tự nguyện chia sẻ.
- Level 3: từ vựng cứu hỏa và sáng tạo; dùng câu điều kiện để nói ước mơ.
- Phát âm: trọng âm âm tiết một của `teacher`, `dentist` và đuôi schwa nhẹ theo nguồn.
- Khích lệ ý tưởng trước, sau đó mới hỗ trợ phát âm; lời khen do Teacher diễn đạt linh hoạt.

## 5. Module registry và định tuyến runtime

Tạo một module curriculum registry có interface nhỏ:

```python
list_units() -> tuple[UnitSummary, ...]
get(unit_id: str) -> UnitCurriculum
```

Registry chịu trách nhiệm khám phá danh sách được cho phép, nạp một lần, validation và lỗi `unknown unit`. Caller không cần biết đường dẫn thư mục hoặc cache. Đây là seam dùng chung cho API, runtime, eval và voice.

Runtime tạo TurnService cho từng curriculum đã đăng ký rồi đặt sau một module định tuyến có cùng interface `process(state, learner_text, turn_id)`. Module này chọn implementation bằng `state.unit_id`; routes và Pipecat không tự nạp curriculum và không có nhánh `if unit == ...`.

Comparison/review workbench nếu được gọi cũng phải định tuyến bằng Unit của session. Session đã lưu Unit 1 tiếp tục chạy bình thường vì `LessonState` đã có `unit_id`.

## 6. API và trạng thái session

Thêm endpoint đọc-only liệt kê Unit:

```text
GET /api/units
```

Mỗi phần tử trả tối thiểu `id`, `grade`, `unit`, `title`. Dữ liệu này đến từ registry, không nhân bản trong frontend.

Tạo/reset session nhận body bắt buộc:

```json
{"unit_id": "grade05.unit02"}
```

Backend xác nhận Unit tồn tại trước khi ghi session. Fresh state dùng `curriculum.id`, stage `warm-up` và hoạt động mở đầu đã định nghĩa trong curriculum. Một session đang hoạt động không được đổi `unit_id`; muốn đổi Unit phải tạo/reset session mới. Turn route luôn đối chiếu `state.unit_id` với service được định tuyến.

Response `SessionView` bổ sung metadata đủ cho UI hiển thị tên Unit mà không hard-code. Request Unit không tồn tại trả HTTP 400 với mã lỗi ổn định. Stored session cũ không được tự động đổi Unit.

## 7. Web và voice

Khi chưa có session, web tải `/api/units` và hiển thị Unit 1–5 để người dùng chọn. Chọn một Unit mới gọi create/reset với `unit_id`. Header, eyebrow và state inspector dùng metadata của session. Nút New Session giữ Unit hiện tại; UI có hành động riêng để quay lại chọn Unit.

Voice vẫn nhận `session_id`. Worker đọc persisted session, sau đó module định tuyến chọn đúng TurnService bằng `state.unit_id`. Không truyền một `unit_id` thứ hai qua WebRTC vì hai nguồn có thể lệch nhau. Voice, text và resume vì vậy dùng cùng một nguồn sự thật.

## 8. Xử lý lỗi

- Workbook thiếu sheet, Unit hoặc anchor hợp lệ: importer dừng với lỗi cụ thể.
- Nội dung chuẩn hóa xung đột ID hoặc pattern: validation dừng; không chọn một bản ngẫu nhiên.
- Unit directory thiếu file hoặc reference: registry không công bố Unit đó và startup/test thất bại.
- Request Unit không tồn tại: HTTP 400, không tạo session.
- Stored session có Unit không còn trong registry: trả lỗi cấu hình rõ ràng, không chạy bằng Unit 1 thay thế.
- Teacher/Evaluator lỗi: giữ nguyên quy tắc hiện tại, không tăng số lần sai và không chuyển stage.
- Dữ liệu cá nhân xuất hiện trong Unit 2/3: lọc theo đường privacy hiện tại trước model và không phản chiếu lại trong lời cô.

## 9. Kiểm thử và tiêu chí hoàn thành

### 9.1. Curriculum/source

- Parametrized importer/source-lock test cho Unit 1–5.
- Test raw cell/value cho toàn bộ vùng A5:M16 cần dùng.
- Test regression ô gộp, Unit boundary, review Lesson 3, number-list và slash-group.
- `load_unit` thành công và mọi reference resolve cho Unit 1–5.
- Mỗi taught vocabulary có đúng một cơ hội giới thiệu riêng trước practice.
- Không có nội dung của Unit này xuất hiện trong Unit khác.

### 9.2. Teaching behavior

Mỗi Unit có test tối thiểu cho:

- hành trình stage đầy đủ;
- câu đúng target form;
- câu đúng nghĩa nhưng khác mẫu;
- sai lần một và hỗ trợ;
- sai lần hai rồi chuyển, đưa vào review;
- hỏi nghĩa;
- nói tiếng Việt;
- im lặng;
- lạc đề;
- Free Talk ôn mục chưa vững;
- kết thúc và summary đúng bằng chứng.

Unit 2 có test riêng không yêu cầu/lặp địa chỉ thật. Unit 3 dùng nhân vật hư cấu. Unit 4 không hỏi tài khoản Internet. Unit 5 không bịa nghề hoặc thông tin gia đình của trẻ.

### 9.3. API/web/voice

- API list Unit và tạo session cho từng Unit.
- Unknown Unit bị từ chối trước khi ghi dữ liệu.
- Text turn định tuyến đúng objective của Unit đã chọn.
- UI chọn Unit, hiển thị title, tạo lại session và resume đúng Unit.
- E2E đi ít nhất từ Unit selector qua Warm-up đến hoạt động đầu tiên cho Unit 2–5.
- Voice smoke thực tế xác nhận session Unit 2–5 không đọc prompt hoặc target của Unit 1.

### 9.4. Điều kiện báo hoàn thành

Chỉ báo hoàn thành khi:

1. Unit 2–5 nạp và chạy được qua API/text;
2. UI thực sự chọn và hiển thị đúng Unit;
3. các source-lock và behavioral tests đạt;
4. focused voice suite đạt trong môi trường Pipecat;
5. ít nhất một đường browser/voice khả thi được kiểm tra thực tế;
6. mọi giới hạn chưa chạy được được nêu rõ, không đánh đồng focused suite với full suite.

## 10. Trình tự triển khai

Triển khai theo lát dọc để tránh nhân bốn sai sót:

1. sửa importer và thêm source-lock cho Unit 2–5;
2. tạo registry, API contract và runtime router;
3. hoàn thiện Unit 2 cùng test text/API/web;
4. xác minh Unit 2 qua browser/voice;
5. dùng seam đã kiểm chứng để thêm Unit 3, 4, 5;
6. chạy regression Unit 1 và full verification phù hợp môi trường.

Unit 2 là lát dọc kiểm chứng kiến trúc, không phải bản MVP cuối. Công việc chỉ hoàn thành khi cả Unit 2–5 đạt tiêu chí ở trên.
