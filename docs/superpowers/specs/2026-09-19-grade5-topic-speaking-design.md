# Phòng luyện nói theo chủ đề — lớp 5

Ngày: 2026-09-19. Trạng thái: chờ người dùng duyệt đặc tả; chưa phê duyệt triển khai.

## 1. Mục tiêu đã thống nhất

Phòng độc lập với bài học theo kịch bản và Free Talk cuối Unit 1. Ưu tiên sự tự tin, hứng thú; đồng thời giúp trẻ diễn đạt tốt hơn. Bản đầu phục vụ lớp 5. Học sinh chọn chủ đề hoặc nói/nhập chủ đề riêng, chọn từ gợi ý hoặc tự nhập từ muốn luyện. Lấy lớp học làm điểm khởi đầu, điều chỉnh hỗ trợ theo bằng chứng trong hội thoại.

Thành công nghĩa là trẻ bắt đầu được cuộc trò chuyện, nhận hỗ trợ khi bí, có cơ hội chủ động nói và vận dụng từ đã chọn. Không đồng nhất hoàn thành phiên với thành thạo từ vựng.

## 2. Phạm vi và lựa chọn thiết kế đề xuất

Ba hướng đã cân nhắc: chatbot với một prompt duy nhất đơn giản nhưng khó kiểm chứng điều chỉnh; mở rộng bộ điều phối Unit 1 tạo phụ thuộc vào học liệu; mô-đun hội thoại riêng dùng chung hạ tầng cho phép kiểm thử và giữ độc lập. Chọn hướng thứ ba.

Các mặc định dưới đây là đề xuất cần duyệt, không phải yêu cầu người dùng đã nói rõ:

- Trang `/speaking`, nhãn Phòng luyện nói lớp 5; có lối vào từ trang chính.
- Chủ đề ban đầu: Animals, Food, School, Hobbies, Family and friends, Places and travel. Có ô chủ đề riêng và lựa chọn nói chủ đề bằng micro.
- Gợi ý tối đa 8 từ theo chủ đề; chọn hoặc nhập 1–5 từ cho một phiên. Nhập nhiều hơn thì yêu cầu chọn nhóm đầu, không âm thầm bỏ từ.
- Chuẩn hóa từ trùng, kiểm tra nghĩa và tính phù hợp với chủ đề; giải thích ngắn khi cần trẻ sửa lựa chọn. Từ chưa biết có nghĩa tiếng Việt và ví dụ ngắn để nghe.
- Luyện bằng micro; nhập văn bản là đường thay thế khi micro không dùng được và phục vụ kiểm thử.
- Không giới hạn thời gian cứng; trẻ kết thúc bằng nút hoặc yêu cầu rõ ràng. Đổi chủ đề kết thúc phiên hiện tại và mở phần chọn cho phiên mới.
- Chưa làm lớp 1–4, bảng quản trị giáo viên, xếp hạng, thi chứng chỉ hoặc hồ sơ trình độ xuyên phiên.

## 3. Trải nghiệm hội thoại

Luồng: chọn chủ đề → chọn từ → bắt đầu tình huống ngắn → trò chuyện linh hoạt → kết thúc và tổng kết.

Tình huống tạo lý do nói, không có danh sách câu trả lời bắt buộc. Ví dụ Food: cùng chuẩn bị picnic; Animals: chăm sóc thú cưng tưởng tượng. Trẻ có thể kể chuyện riêng, hỏi lại hoặc đề xuất hướng khác trong chủ đề. AI phản hồi ý trẻ trước khi hỏi tiếp; mỗi lượt tối đa một câu hỏi chính, thường 1–2 câu ngắn. Không hỏi dồn hoặc luôn bắt trẻ nhắc lại.

Từ mới: giải thích tại thời điểm cần, làm mẫu ngắn, tạo cơ hội dùng lại trong ngữ cảnh khác. Không nhồi mọi từ vào một lượt. Chấp nhận câu có nghĩa dù khác mẫu. Sửa nhẹ bằng cách diễn đạt lại đúng; hỏi làm rõ nếu không hiểu. Hỗ trợ tiếng Việt ngắn khi trẻ yêu cầu hoặc hỗ trợ tiếng Anh không đủ, rồi quay lại hội thoại tiếng Anh.

Ví dụ: trẻ chọn rabbit, carrot, feed. AI cùng trẻ đặt tên thỏ, hỏi cho thỏ ăn gì, đưa lựa chọn khi trẻ bí, rồi tạo lượt sau để trẻ tự dùng feed. Một từ trả lời phù hợp vẫn được ghi nhận; không ép thành câu dài ngay.

## 4. Điều chỉnh và bằng chứng

Ba mức hỗ trợ nội bộ: nhiều hỗ trợ, câu ngắn độc lập, mở rộng ý. Đây không phải nhãn CEFR hay điểm năng lực. Khởi đầu lớp 5 bằng câu hỏi ngắn về sở thích; chưa đủ dữ liệu thì giữ mức.

Theo dõi riêng: hiểu và đáp đúng ý, mức hỗ trợ đã nhận, khả năng nối ý/hỏi lại và cách dùng từng từ. Sau ba lượt hợp lệ liên tiếp thể hiện độc lập ở mức hiện tại, tăng yêu cầu một bước. Khi trẻ yêu cầu trợ giúp thì hỗ trợ ngay; sau hai lượt khó khăn hợp lệ liên tiếp thì giảm yêu cầu một bước. Thành công có gợi ý không tính vào chuỗi độc lập. Đây là ngưỡng khởi đầu để kiểm thử, không phải kết luận nghiên cứu.

Thang hỗ trợ: chờ trẻ → hỏi lại dễ hơn → hai lựa chọn → đầu câu → mẫu ngắn và chuyển tiếp. Trẻ không phải vượt qua từng nấc mới được nói tiếp. Không suy luận trình độ từ im lặng, sự ngại ngùng, lỗi mạng hay âm thanh không rõ; các lượt đó không tăng bộ đếm năng lực.

Mỗi từ lưu số lần gặp, dùng có hỗ trợ, dùng độc lập, và tham chiếu lượt minh chứng. Không dùng lời AI làm bằng chứng học sinh; lượt lặp mẫu không tính độc lập. Tổng kết nêu ví dụ thực tế và một gợi ý luyện tiếp; chỉ ghi chưa quan sát khi không có bằng chứng. Không báo đã thành thạo từ một lần dùng đúng; không chấm phát âm từ transcript.

## 5. Kiến trúc và hợp đồng

Hiện trạng đã đọc: `backend/src/luna_tutor/api/routes.py` khởi tạo `grade05.unit01`; trang chính dùng `TutorShell`; thư mục `voice/server` có bot giọng nói và runtime kiểm thử văn bản. Không đưa trạng thái phòng mới vào `LessonState`, bộ điều phối Unit 1 hoặc hàng đợi ôn bài của Unit 1.

Mô-đun `speaking` riêng gồm:

- Danh mục/gợi ý: nhận chủ đề và lớp, trả từ cùng nghĩa và ví dụ; xác thực đầu ra mô hình.
- Trạng thái phiên: mã phiên, lớp 5, chủ đề, từ đích, tình huống, mức hỗ trợ, bộ đếm, bằng chứng từ, lịch sử, phiên bản và trạng thái active/completed.
- Đánh giá lượt: nhận lời trẻ, lời AI thực sự đã phát, hỗ trợ đã cung cấp và ngữ cảnh gần; trả bằng chứng có cấu trúc, không tự thay trạng thái.
- Chính sách hội thoại: nhận trạng thái và bằng chứng, quyết định hỗ trợ/mở rộng/tiếp tục/kết thúc theo quy tắc mục 4.
- Sinh lời AI: nhận quyết định cùng ngữ cảnh, tạo lời tự nhiên, ngắn, phù hợp trẻ; không tự ghi tiến độ.
- Kho phiên: bảng riêng trong SQLite, ghi nguyên tử với kiểm tra phiên bản và khóa định danh lượt chống ghi lặp. Tái sử dụng kết nối lưu trữ, không tái sử dụng mô hình dữ liệu Unit.

API đề xuất dưới `/api/speaking`: lấy chủ đề, gợi ý từ, tạo/liệt kê/đọc phiên, gửi lượt và kết thúc. Gửi lượt gồm `turn_id`, `expected_state_version`, nội dung và thông tin chất lượng nhận dạng nếu có. Phản hồi chứa trạng thái đã cam kết và lời AI. Mỗi phiên chỉ xử lý một lượt sinh phản hồi tại một thời điểm; gửi lại cùng lượt không sinh bằng chứng trùng.

Web dùng thành phần chọn chủ đề/từ, kết nối micro, hội thoại và tổng kết riêng. Adapter giọng nói gọi cùng dịch vụ hội thoại như đường văn bản. Giữ cấu hình provider đang có; xác minh API Pipecat và client kết nối từ nguồn hiện hành khi viết kế hoạch. Nếu câu AI bị ngắt, chỉ phần thực sự phát được ghi là nội dung trẻ đã nghe; không cộng bằng chứng cho lời chưa phát.

Luồng dữ liệu: âm thanh → nhận dạng → chuẩn hóa/khử dữ liệu nhạy cảm → đánh giá → chính sách → sinh lời → lưu lượt → phát âm thanh. Sự kiện phát xong/bị ngắt cập nhật bản ghi phát, không tạo thêm lượt học sinh.

## 6. Lỗi và giới hạn

Không nghe rõ thì xin nói lại, không bịa transcript hoặc hạ mức. Lỗi model/schema không cập nhật tiến độ; thông báo ngắn và cho thử lại. Lỗi phát âm thanh giữ văn bản để đọc/nghe lại và đánh dấu chưa phát xong. Mất kết nối giữ các lượt đã lưu; kết nối lại nạp phiên, không tự phát lại câu hỏi như lượt mới. Yêu cầu kết thúc phải được đáp ứng kể cả còn từ chưa luyện.

Chủ đề và từ trẻ nhập là dữ liệu, không có quyền sửa chỉ dẫn hệ thống. Dùng xử lý dữ liệu nhạy cảm sẵn có ở ranh giới đầu vào. Chủ đề không phù hợp lứa tuổi được chuyển hướng nhẹ sang lựa chọn phù hợp. Không hỏi địa chỉ, số điện thoại hoặc tên trường thật để duy trì cuộc trò chuyện.

Trong workspace đang có thay đổi chưa commit cho OpenPronounce và bot giọng nói. Kế hoạch phải bảo toàn các thay đổi này và kiểm tra lại trước khi tích hợp; không ghi đè hoặc đưa chúng vào commit đặc tả.

## 7. Kiểm chứng và tiêu chí chấp nhận

1. Vào thẳng phòng lớp 5, chọn chủ đề/từ và nói được; không cần phiên Unit 1.
2. Chủ đề riêng và từ tự nhập hoạt động; giới hạn, trùng từ và đầu ra gợi ý lỗi được xử lý rõ ràng.
3. Cùng tình huống nhưng trẻ trả lời khác nhau tạo các nhánh phù hợp; không cưỡng ép một đáp án.
4. Kiểm thử chính sách bằng chuỗi bằng chứng độc lập: tăng/giảm mức đúng ngưỡng; lượt không rõ không tác động mức.
5. Kịch bản hội thoại gồm trẻ mới học, khá, dùng tiếng Việt, hỏi lại, lạc chủ đề, im lặng, muốn dừng; xác nhận phản hồi có hỗ trợ và không hỏi dồn.
6. Không ghi dùng độc lập khi lặp mẫu; không bịa bằng chứng tổng kết; có thể kết thúc khi chưa dùng hết từ.
7. Thử gửi lặp, phiên bản cũ, lỗi provider và kết nối lại: không mất/lặp lượt và không ghi tiến độ sai.
8. Chạy vòng kiểm thử văn bản nhanh, sau đó kiểm thử âm thanh thật cho nhận dạng, ngắt lời, phát lại và kết thúc; kiểm tra hồi quy luồng Unit 1.
9. Trước kiểm thử live, xác nhận cấu hình và sự hiện diện của khóa provider mà không in giá trị; khóa thiếu phải được cung cấp trước khi chạy.

## 8. Cơ sở tham khảo và giới hạn

- Cambridge: tạo lý do giao tiếp qua trò chơi, đóng vai và kể chuyện: https://www.cambridgeenglish.org/learning-english/parents-and-children/your-childs-interests/practising-speaking-outside-the-classroom/
- Cambridge: phân hoạt động theo năng lực, không gán cứng lớp học: https://www.cambridgeenglish.org/learning-english/parents-and-children/activities-for-children/
- British Council: chuẩn bị ngôn ngữ cho đóng vai: https://www.teachingenglish.org.uk/comment/207946
- Han & Lee (2024): nguyên tắc thiết kế chatbot luyện nói tiểu học, hỗ trợ và phản hồi cá nhân hóa: https://www.nature.com/articles/s41599-024-02646-w

Nguồn hỗ trợ định hướng sư phạm; giới hạn từ, số lượt và kiến trúc trong đặc tả là lựa chọn sản phẩm cần kiểm nghiệm với trẻ, không phải chuẩn đã được các nghiên cứu xác nhận.
