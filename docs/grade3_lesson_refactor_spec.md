# Quyết định refactor dạy học theo kịch bản

Ngày bắt đầu: 2026-09-23
Nhánh: `codex/refactor-scripted-teaching-discussion`
Trạng thái: logic và bốn lesson lớp 3 đã được refactor trên nhánh này; còn cần kiểm chứng Voice với mic thật.

Tệp này **chỉ ghi các quyết định đã được người dùng chốt**. Nội dung thảo luận, phương án đề xuất và câu hỏi chưa trả lời không ghi vào đây. Khi có quyết định mới, cập nhật nội dung và nhật ký bên dưới để dùng làm căn cứ triển khai.

Ngoại lệ theo yêu cầu người dùng: mục **để bàn sau** ở cuối tệp chỉ ghi tên vấn đề cần quay lại, không ghi phương án hoặc kết luận chưa chốt.

## Phạm vi đã chốt

- Refactor cách dạy học theo kịch bản cho lớp 3 vì luồng hiện tại quá rườm rà. Bản thiết kế này chỉ áp dụng cho lớp 3.
- Sau phần kịch bản sẽ bàn tiếp về Jev Evaluator, LLM Teacher, cách dạy, ngoại lệ và `description` đưa cho Teacher xử lý ngoại lệ.
- Bắt đầu bằng luồng thực hiện theo kịch bản. Việc triển khai đã được người dùng yêu cầu ngày 2026-09-24.
- Không đưa im lặng, thông tin liên hệ nhạy cảm, lệnh kết thúc/tạm dừng và Free Talk vào **bảng năm mã Jev cho lượt kịch bản**. Quyết định này không xóa các chức năng đó khỏi sản phẩm.
- Khi triển khai các phần liên quan Pipecat, **ưu tiên dùng tính năng và API Pipecat đã hỗ trợ; không tự viết lại logic của Pipecat**. Chỉ viết phần logic riêng khi đã kiểm tra tài liệu và phiên bản Pipecat đang dùng mà Pipecat không có cơ chế đáp ứng yêu cầu; giới hạn phần viết riêng vào chỗ còn thiếu.

## Hợp đồng thực hiện kịch bản

### Đơn vị một lượt

- **Kịch bản gồm các mục có `type` là `practice`, `narration` hoặc `end`.** Mỗi mục có `say` để Luna đọc nguyên văn. Chỉ mục `practice` có `learner_goal`, mô tả việc học sinh cần thực hiện mà không buộc vào một câu đáp án cố định. `narration` và `end` không có `learner_goal`, không đợi học sinh trả lời và không gọi Jev.
- `practice`: phát `say`, chờ học sinh chủ động nói rồi dùng Jev đánh giá theo **một** `learner_goal` của mục đó. `narration`: phát `say` xong tự chuyển đến mục kế tiếp. `end`: phát `say` kết bài xong thì hoàn tất bài học, không chuyển đến mục khác và không mở mic cho bài đã kết thúc. `end` là mục cuối của bài.
- Mỗi mục `practice` có **một mục tiêu** để so với query của học sinh. Nhiều mục có thể cùng dạy một từ hoặc mẫu câu, nhưng mỗi mục `practice` được đánh giá theo `learner_goal` đang hoạt động của chính nó.
- `learner_goal` cần nêu rõ kiến thức hoặc mẫu ngôn ngữ bắt buộc khi bài học yêu cầu; với thông tin do học sinh tự chọn, Teacher giữ nguyên nội dung em đã nói khi sửa cách diễn đạt. Prompt không thể suy ra tiêu chí chưa được nêu trong mục tiêu.
- **Cách viết `learner_goal` đã chốt: kết hợp mục tiêu cụ thể với ranh giới chấp nhận.** Trong cùng một trường văn bản, ghi (1) việc học sinh cần làm, (2) từ/cấu trúc bắt buộc nếu bài đang luyện đúng từ/cấu trúc ấy, (3) phần học sinh được tự chọn hoặc những cách diễn đạt tương đương được chấp nhận, và (4) một ranh giới dễ gây nhầm khi đánh giá. Chỉ ghi ràng buộc thực sự thuộc mục tiêu bài; không biến `learner_goal` thành danh sách mọi câu sai có thể xảy ra. Không thêm field YAML riêng cho các mục này.
- Ví dụ **luyện đúng mẫu câu**: `say: "What is your name? Say: My name is..."`; `learner_goal: "Học sinh giới thiệu tên mình bằng câu 'My name is [tên]'. Tên do học sinh tự chọn. Cần dùng đúng 'My name is'; chỉ nói tên hoặc dùng 'My name are' thì chưa đạt."` Ở lượt này, `I'm Quang` đúng ngữ pháp nhưng không đạt yêu cầu luyện mẫu `My name is`.
- Nếu bài chỉ yêu cầu **giới thiệu tên bằng tiếng Anh**, `learner_goal` phải nói rõ có thể dùng `My name is [tên]` hoặc `I'm [tên]`; không tự áp ràng buộc dùng `My name is` từ ví dụ trên cho mọi kịch bản. Jev dựa trên mục tiêu của chính lượt hiện tại; Teacher giữ lại tên học sinh tự chọn khi sửa cách nói.
- Trong học liệu lớp 3 hiện tại, có `say` chính và các mục `more`, một số mục `more` không có `accept` và chỉ dùng để nói. Khi chuyển sang thiết kế mới, lời cần học sinh đáp trở thành `practice` với `learner_goal`; lời chỉ phát trở thành `narration`; lời kết bài trở thành `end`. Việc thiếu `learner_goal` ở `practice` hoặc có `learner_goal` ở `narration`/`end` là dữ liệu không hợp lệ, không được âm thầm coi như lời chỉ đọc.
- **Nguồn chuyển đổi là các lesson lớp 3 đang có** trong `curriculum/grade-03/unit-01/lesson-*/content.yaml`. Dùng lại nội dung và thứ tự dạy hiện có làm cơ sở; khi chuyển `say`/`more`/`accept` sang ba loại mục mới, được chỉnh những chỗ cần thiết để mỗi `practice` có một `learner_goal` rõ ràng và lời chỉ đọc không bị đánh giá. Không cần soạn một bộ lesson mới từ đầu.
- Quyết định ban đầu là người dùng tự viết và chỉnh học liệu bằng tay. Ngày 2026-09-24, người dùng yêu cầu refactor luôn bốn lesson thật. Các tiêu chí cũ chỉ nhận biết được qua âm thanh đã được đổi thành mục tiêu có thể đối chiếu với transcript chữ; người biên soạn vẫn có thể tiếp tục chỉnh `learner_goal` trực tiếp.

Ví dụ dạng YAML đã chốt:

```yaml
- type: practice
  say: "Can you say: Hello?"
  learner_goal: "Học sinh nói lời chào Hello."
- type: narration
  say: "Scene done! You just had a real conversation in English!"
- type: end
  say: "Con đã hoàn thành bài học hôm nay!"
```

### Luồng bình thường

1. Luna đọc **nguyên văn** `say` của mục kịch bản hiện tại.
2. Chỉ ở mục `practice`, hệ thống chờ học sinh trả lời rồi đưa query cùng `learner_goal` hiện tại cho **Jev** để so sánh. `narration` và `end` không nhận câu trả lời để đánh giá.
3. Khi câu trả lời đạt mục tiêu và không có ngoại lệ, hệ thống chuyển sang mục kế tiếp và đọc lời kịch bản kế tiếp **nguyên văn**. Các mục `narration` trên đường đi tự phát rồi đi tiếp; mục `end` phát xong thì hoàn tất bài. Lời bình thường không được LLM Teacher viết lại.

### Luồng ngoại lệ

- **Tất cả trường hợp ngoại lệ đưa qua LLM Teacher** để tạo lời xử lý.
- Jev dùng để so query với mục tiêu của lượt hiện tại. Jev trả **một mã kết quả duy nhất cho cả lượt**, thay cho nhiều nhãn phải ghép với nhau trong code.
- Jev chỉ trả một trong **năm mã** dưới đây. Tên mã mô tả ý nghĩa lời học sinh so với `learner_goal` hiện tại; code dựa vào mã để chọn đường xử lý.
- Tên kiểu kết quả chứa năm mã là `TurnEvaluation`. `turn_evaluation` là **ID câu hỏi** trong `questions` của Jev Decisions API. Kết quả API nằm tại `answers.turn_evaluation.choice`; code kiểm tra và chuyển giá trị đó thành `TurnEvaluation` nội bộ.

| Mã Jev | Ý nghĩa | Xử lý và description cho Teacher |
| --- | --- | --- |
| `PASSED` | Học sinh đạt `learner_goal` hiện tại; không có nhu cầu khác cần trả lời. | Không gọi Teacher; chuyển đến mục kế tiếp và đọc nguyên văn các lời `say` tương ứng. |
| `ATTEMPT_FAILED` | Học sinh đã thử trả lời nhưng chưa đạt `learner_goal`. | Code đếm số lần sai và chọn rule theo luồng bốn lần sai dưới đây. |
| `OTHER_INTENT` | Học sinh nói điều có ý nghĩa nhưng chưa thực hiện `learner_goal`; có thể liên quan bài học hoặc là một ý định giao tiếp khác. | Teacher đáp đúng nội dung query với history, rồi dẫn về mục tiêu; không tính sai, giữ mục tiêu hiện tại. |
| `PASSED_WITH_REPLY` | Học sinh đạt `learner_goal` và lời nói còn cần Luna đối thoại; bao gồm khi đặt câu hỏi cho Luna chính là mục tiêu. | Teacher đáp trước; sau đó code chuyển đến mục kế tiếp và phát nguyên văn `say` tương ứng. |
| `UNCLEAR_INPUT` | Query/transcript không đủ rõ hoặc không đủ tin cậy để xếp vào bốn nhóm trên. | Teacher hỏi lại ngắn, không tính sai và giữ lượt hiện tại. |

- Câu học sinh có nhiều ý nhưng hiểu rõ không tự động thuộc `UNCLEAR_INPUT`. Jev trả **một mã cho cả lượt**, dựa vào mức độ thực hiện `learner_goal`: đã đạt và có nội dung cần Luna đáp → `PASSED_WITH_REPLY`; đã đạt và không cần đáp thêm → `PASSED`; đã thử nhưng chưa đạt → `ATTEMPT_FAILED`; chưa thử nhưng có ý định giao tiếp rõ → `OTHER_INTENT`. Chỉ chọn `UNCLEAR_INPUT` khi thông tin không đủ tin cậy để xác định các điều trên. Ví dụ mục tiêu là nói tên mình, “My name is Quang. What's your name?” thuộc `PASSED_WITH_REPLY`.
- **Ranh giới khi mục tiêu là hỏi Luna:** câu hỏi đúng của học sinh luôn thuộc `PASSED_WITH_REPLY`, kể cả khi câu hỏi ấy là toàn bộ lời học sinh và không có ý phụ; Luna phải trả lời trước khi chuyển lượt. `PASSED` chỉ dùng khi Luna không còn nội dung cần đáp. Nếu học sinh nói một câu kể/trả lời về **đúng chủ đề được yêu cầu hỏi** thay vì đặt câu hỏi, đó là `ATTEMPT_FAILED` (ví dụ mục tiêu hỏi Luna cô có khỏe không nhưng học sinh nói “I'm fine.”). Một câu rõ nghĩa về chủ đề khác, không thử thực hiện mục tiêu, là `OTHER_INTENT` (ví dụ ở cùng lượt học sinh nói “My name is An.”). Quy tắc này được viết trực tiếp vào `instructions` và `criteria` của YAML Jev để tránh hai mã đạt mục tiêu chồng nghĩa.
- Câu hỏi Jev duy nhất cho lượt kịch bản được ghi ở [YAML](../backend/src/luna_tutor/prompts/grade3_jev_rubric.yaml) với `type: choice`, `instructions` và năm `criteria`; runtime đọc trực tiếp YAML này. Phần hướng dẫn viết bằng tiếng Anh, nội dung học sinh và history giữ nguyên lời thực tế.
- Rubric Jev đã được thử trực tiếp với Decisions API trên các transcript chữ mẫu. Bộ thử cũ gồm nhiều phạm vi nên các tỷ lệ khớp trước đây không được dùng làm bằng chứng cho thiết kế lớp 3. Cần kiểm thử lại bằng các tình huống lớp 3 trước khi triển khai.
- Request Jev dùng `model`, `state`, `questions`. Trong `state`, đưa `learner_goal`, `learner_query` mới nhất và `history` theo thứ tự thời gian của lượt hiện tại. `history` gồm lời Luna đã phát (`role: assistant`) và lời học sinh trước đó (`role: user`), kể cả `say` và các lời sửa/hỗ trợ; không lặp `learner_query` mới nhất trong history. Đây là dữ liệu JSON cho Jev, không phải chat messages của API. Không đưa số lần sai, `say` kế tiếp hoặc description cho Teacher vào phần nội dung Jev cần đánh giá.
- Code đọc `answers.turn_evaluation.choice`, kiểm tra `type: choice` và mã thuộc đúng năm giá trị đã chốt. Các trường xác suất/độ tin cậy nếu API trả thêm không thuộc `TurnEvaluation` nội bộ đã chốt.
- Mỗi **mã ngoại lệ** chọn `description` hướng dẫn LLM Teacher xử lý tình huống tương ứng; `ATTEMPT_FAILED` dùng rule theo số lần sai.
- Với câu trả lời sai, Jev trả cùng một mã `ATTEMPT_FAILED` ở mọi lần thử. **Code đếm số lần sai của `learner_goal` hiện tại** và chọn rule tương ứng; Jev không cần trả mã riêng cho từng lần thử.
- Teacher không viết lại `say` mới; khi chuyển lượt, code phát nguyên văn lời kịch bản.
- Khi xử lý ngoại lệ, LLM Teacher cần xem lại lịch sử các câu học sinh đã nói (`query`) và lời Luna/hệ thống đã phát (`output`) để trả lời đúng mạch hội thoại.
- Developer rule cho bốn mã ngoại lệ được ghi ở dưới; `PASSED` không gọi Teacher.

### Ngữ cảnh cho Teacher qua Pipecat

- Với cả Voice và Text, **dùng cùng logic hội thoại và history cho Teacher**. Thiết kế dùng `LLMContext` và context aggregator của Pipecat, giữ các lượt hội thoại qua chuyển node bằng `ContextStrategy.APPEND`; không tự dựng rồi gửi lại một bản history riêng trong payload Teacher. Đây là hướng refactor, chưa phải hành vi của runtime hiện tại.
- Teacher dùng LLM service của Pipecat trực tiếp để nhận context đó. Lời học sinh vừa nói đi vào context như message `user`; lời Luna thực sự phát, gồm `say` nguyên văn và lời Teacher sửa/hỗ trợ, đi vào context như message `assistant`. `say` kế tiếp vẫn do code phát nguyên văn và phải xuất hiện trong context sau khi phát để Teacher hiểu mạch hội thoại.
- Teacher đọc `say` hiện tại từ history `assistant` đã có trong Pipecat context; **không gửi thêm một bản sao `say` trong developer rule hoặc payload riêng**. Những rule sửa lỗi nhắc đến `say` là nhắc đến lời Luna đã phát trong history. Nếu tóm tắt tự động làm mất chi tiết mẫu cần sửa trong một lượt luyện kéo dài, phải kiểm chứng tình huống thực tế rồi mới quyết định xử lý; không tạo bản history thứ hai để phòng ngừa từ trước.
- `system` giữ vai trò Luna và các quy tắc ổn định. Với ngoại lệ, code chọn đúng **một** description và đưa nó cùng `learner_goal` hiện tại vào hướng dẫn `developer` của lượt Teacher; Teacher không tự chọn rule theo số lần sai. Không gửi trùng query mới nhất ở một field riêng khi Pipecat đã ghi nó trong `user` context. `PASSED` không gọi Teacher.
- **Chốt phương án 3 để quản lý rule theo lượt:** Pipecat tiếp tục giữ các message hội thoại `user`/`assistant` và bản tóm tắt bằng `APPEND`; trước mỗi lần gọi Teacher, code dùng cơ chế cập nhật context của Pipecat để bỏ **rule `developer` theo lượt cũ** và đặt **một rule `developer` mới** đã chọn từ kết quả Jev và số lần sai. Không tự dựng hoặc gửi lại history dưới dạng payload Teacher. Ví dụ từ sai lần 1 sang sai lần 2: giữ nguyên câu học sinh và lời Teacher trước đó, thay hướng dẫn “sửa một lỗi” bằng hướng dẫn “giảm độ khó”.
- Việc thay rule phải được áp dụng đúng thứ tự trong pipeline trước khi Teacher sinh lời; không xóa lời hội thoại, `say` đã phát, hay tóm tắt của Pipecat. Đây là quản lý **phạm vi hiệu lực của hướng dẫn**, không phải tự quản lý history. Pipecat có thể tóm tắt hoặc bỏ message `developer` cũ; vì vậy trước **mỗi** lần gọi Teacher vẫn phải đặt rule hiện tại và kiểm tra context thực gửi tới model chỉ có rule này, kể cả sau tóm tắt và chuyển node.
- **Chọn cấu hình tóm tắt tự động mặc định của Pipecat** cho context aggregator phục vụ Teacher: bật `LLMAssistantAggregatorParams(enable_auto_context_summarization=True)` và không ghi đè `auto_context_summarization_config`. Pipecat 1.11.0 kích hoạt ở khoảng 8.000 token ước tính hoặc 20 message `user`/`assistant` mới; giữ 4 message gần nhất nguyên văn, tóm tắt phần cũ. Các ngưỡng này không phải số message tối đa được lưu. `say` hoặc lời sửa cũ có thể chỉ còn trong bản tóm tắt nếu lượt luyện kéo dài; khi triển khai cần kiểm tra Teacher vẫn xử lý đúng các ca đó.
- Runtime hiện tại dùng `BoundedTeacherLLM` chuyển `TeacherTurnRequest` tới `GeminiTeacher`, nơi model nhận `system` và JSON `user`; Voice Flows dùng `ContextStrategy.RESET`. Các phần này cần thay đổi để đạt thiết kế trên cho cả Voice và Text.

### Voice và Text dùng cùng luồng dạy học

- Cả hai cách học dùng **cùng học liệu lớp 3**, một `learner_goal` cho mỗi `practice`, cùng Jev `TurnEvaluation`, bộ đếm lần sai, rule Teacher và quy tắc chuyển mục. `say` luôn giữ nguyên nội dung đã biên soạn.
- Voice nhận lời học sinh qua STT và phát lời Luna qua TTS. Text nhận câu học sinh nhập trực tiếp và hiển thị lời Luna dưới dạng chữ; **Text không chạy qua STT hoặc TTS**. Ở Text, việc hiển thị xong toàn bộ lời Teacher/`say` tương ứng với việc phát xong lời ở Voice để cho phép lượt học sinh kế tiếp.
- History của Teacher trong Text cũng ghi câu học sinh là `user` và lời Luna đã hiển thị là `assistant`, gồm `say` và lời Teacher. Việc không dùng TTS không được làm mất lời `say` khỏi history.
- Model Teacher cấu hình trong repo là `google/gemini-3.5-flash-lite`. Ngày 2026-09-24, hai request trực tiếp tới OpenRouter với `system` + `developer` + `user` đều trả HTTP 200 và đúng `DEV_OK`; request thứ hai có chỉ dẫn `user` trái ngược nhưng model vẫn làm theo `developer`. Vì Pipecat OpenRouter 1.11.0 mặc định đổi `developer` thành `user`, khi triển khai LLM service cần bật `supports_developer_role = True` cho model đã thử và kiểm tra request thực gửi giữ đúng vai trò.

### Vòng đời phiên học

- Chỉ giữ trạng thái học tập trong phiên Voice hoặc Text đang hoạt động. Khi học sinh thoát phiên, bỏ context/history của Pipecat, bản tóm tắt, vị trí kịch bản đang học và bộ đếm lần sai; không lưu những dữ liệu này để nối lại phiên.
- Học sinh vào lại sẽ bắt đầu một phiên mới từ đầu kịch bản, với context mới và bộ đếm lần sai `0` cho lượt đầu tiên. `ContextStrategy.APPEND` và tóm tắt tự động chỉ áp dụng **bên trong cùng một phiên**, không nối history giữa hai phiên, ở cả Voice và Text.
- Quyết định này áp dụng cho việc **thoát phiên**. Quy tắc không cho học sinh ngắt lời trong lúc Luna đang phát được ghi bên dưới; sự cố kết nối hoặc phát âm thanh thất bại là lỗi kỹ thuật riêng.

### Điều khiển mic trong phiên Voice

- Mic mặc định **tắt**. Học sinh chủ động ấn nút mic để bắt đầu nói; mic không tự bật khi Luna nói xong hoặc khi chuyển sang `learner_goal` mới. Kết nối Voice có thể tiếp tục hoạt động trong lúc mic tắt.
- Ngay khi học sinh ấn **Gửi** và câu trả lời được nộp để Jev/LLM xử lý, web tắt mic và không cho bật lại trong lúc Jev/LLM đang xử lý hoặc Luna đang phát lời, kể cả trước khi TTS bắt đầu phát. Sau khi Luna đã phát xong toàn bộ lời của lượt đó, hệ thống chỉ **cho phép** ấn nút mic; mic vẫn tắt cho đến khi học sinh thực sự ấn.
- Sau khi nhận lệnh **Gửi** của một lượt, phía server không nhận một lượt học sinh mới để đưa vào Jev/Teacher, thay context hay ngắt lời đang xử lý cho đến khi Luna hoàn tất lời đáp. Chỉ khi một mục `practice` đã phát xong mới có quyền mở mic để trả lời; `narration` và `end` không mở mic. Khóa nút mic ở trình duyệt không thay thế quy tắc này: transcript hoặc tín hiệu nói đến muộn phải được kiểm tra theo lượt và trạng thái xử lý để không hủy LLM/TTS hoặc đếm sai lần thử.
- **Không cho học sinh ngắt lời Luna trong Pipecat**, từ lúc yêu cầu đang được xử lý đến khi phát xong toàn bộ lời Teacher và `say` kế tiếp. Với luồng Voice có nút Gửi, tắt user-turn interruptions; chiến lược bắt đầu lượt theo transcript đặt `enable_interruptions=False`. Tín hiệu lượt nói mới không được hủy Jev/LLM/TTS đang chạy. Việc tắt interruptions không tự bỏ qua transcript/lượt mới; server vẫn phải kiểm tra trạng thái lượt để không xếp thêm câu trả lời ngoài ý muốn.
- Transcript `final` từ STT và hành động **Gửi** là hai sự kiện khác nhau. Quy tắc chốt transcript theo nút Gửi được ghi ngay bên dưới.

### Chốt transcript chỉ bằng nút Gửi

- **Chốt phương án 3:** Trong một lượt nói bình thường, chỉ hành động **Gửi** của học sinh mới yêu cầu chốt transcript. Trẻ ngừng giữa câu không làm hệ thống kết thúc lượt, gọi Jev hoặc phát lời Luna.
- Khi triển khai, dùng chế độ Pipecat của `SonioxSTTService` (`vad_force_turn_endpoint=True`) để **tắt cơ chế Soniox tự phát hiện điểm kết thúc**. Ở chế độ này, Pipecat gửi lệnh `finalize` cho Soniox khi dịch vụ nhận `VADUserStoppedSpeakingFrame`; **Soniox vẫn là bên tạo transcript `final`**, Pipecat nhận và gom transcript. Không mô tả sai thành “Pipecat tự nhận dạng và trả lời nói cuối”. Runtime Voice hiện tại đang dùng `vad_force_turn_endpoint=False` và chưa làm theo thiết kế này.
- Không cấu hình VAD tự phát `VADUserStoppedSpeakingFrame` trong luồng nói có nút Gửi; nếu không, một khoảng ngừng giữa câu vẫn tự yêu cầu Soniox chốt transcript. Dùng cơ chế bắt đầu lượt từ transcript của Pipecat với interruptions đã tắt; cách cấu hình cụ thể phải xác nhận với phiên bản Pipecat khi viết code.
- **Bắt đầu lượt:** trình duyệt chỉ bật mic khi học sinh ấn mic. Mỗi lần mở mic tạo một ID lượt nói ổn định trong phiên và thông báo ID đó cho server. Server chỉ nhận một lượt khi đang chờ học sinh; không nhận lệnh mở lượt trong lúc đã nộp bài, Jev/Teacher đang xử lý hoặc Luna đang phát lời.
- **Nộp lượt:** học sinh ấn Gửi một lần; trình duyệt tắt mic ngay, khóa Gửi/mic và gửi lệnh nộp kèm ID lượt qua kênh thông điệp Pipecat/RTVI. Server kiểm tra ID và trạng thái; lệnh Gửi trùng hoặc muộn không phát thêm yêu cầu chốt. Sau khi âm thanh đã gửi trước nút Gửi đi hết qua transport tới STT, server đưa tín hiệu chốt của Pipecat tới Soniox. **Thứ tự giữa gói âm thanh WebRTC và thông điệp Gửi là điều kiện phải kiểm chứng**, không mặc nhiên coi tắt mic hoặc gửi message là đã xả hết âm thanh.
- **Chờ transcript:** sau yêu cầu chốt, chờ Soniox trả transcript `final` cho lượt đó. Chỉ khi đã nhận phần cuối và Pipecat hoàn tất gom lời nói, hệ thống mới đưa **một query** vào Jev. `final` không tự nộp lượt nếu không có Gửi; không gửi các phần `interim` cho Jev. Transcript muộn hoặc trùng sau khi lượt đã nộp không được mở lượt mới, gọi Jev lần nữa hay thay context Teacher.
- **Không có lời nói hoặc thiếu `final`:** không đưa transcript rỗng/chưa chốt vào Jev. Có đường chờ có giới hạn và thông báo để học sinh thử lại; mic vẫn tắt cho đến khi học sinh chủ động ấn lại. Không dùng thời gian chờ này để tự đoán phần lời còn thiếu. Timeout tự dừng lượt của Pipecat phải được cấu hình sao cho một khoảng ngừng giữa câu không tự đóng lượt trước nút Gửi.
- Khi Luna hoàn tất **toàn bộ** lời đáp và đã phát xong `say` của mục `practice` kế tiếp, server mới mở quyền nhận một lượt nói mới; trình duyệt chỉ bật lại khả năng ấn mic, không tự bật mic. Nếu mục kế tiếp là `end`, hoàn tất bài sau khi phát xong `say` và không mở mic. Cần kiểm chứng ca Teacher sửa xong rồi code đọc `say` kế tiếp để không mở mic giữa hai đoạn lời.
- Bằng chứng trước khi triển khai: thử nghiệm Pipecat 1.11.0 ở `voice/server/experiments/manual_submit_turn_probe.py` xác nhận `VADUserStoppedSpeakingFrame` khiến `SonioxSTTService` gửi `{"type": "finalize"}` khi `vad_force_turn_endpoint=True`, còn chế độ `False` không gửi. Đây là thử nghiệm với WebSocket giả, **chưa** xác nhận âm thanh mic thật, thời điểm gói âm thanh cuối đến STT, transcript Soniox trả về hoặc tích hợp Jev/Teacher. Các trường hợp đó phải được kiểm chứng trong triển khai.

| Lần sai ở cùng `learner_goal` | Lời Teacher | Bước tiếp theo |
| --- | --- | --- |
| 1 | Sửa điểm chưa đạt và mời thử lại. | Học sinh thử lần 2. |
| 2 | Giảm độ khó và mời thử lại. | Học sinh thử lần 3. |
| 3 | Hỗ trợ để học sinh thử lại. | Học sinh thử lần 4. |
| 4 | Nói kết quả/câu đúng cho lượt cũ. | Code phát nguyên văn các `say` tiếp theo; gặp `end` thì hoàn tất bài sau khi phát xong. |

### Bộ đếm lần sai của mục tiêu hiện tại

- Bộ đếm bắt đầu từ `0` khi một mục `practice`/`learner_goal` mới trở thành mục hiện tại. Nó gắn với **mục `practice` đang hoạt động**, không gắn với nguyên văn `learner_goal`: hai mục có cùng câu mô tả mục tiêu vẫn có bộ đếm riêng.
- Mỗi **lượt trả lời mới của học sinh** bằng Voice hoặc Text được Jev phân loại `ATTEMPT_FAILED` làm bộ đếm tăng đúng `1` lần. Giá trị sau khi tăng (`1`–`4`) quyết định developer rule gửi cho Teacher. Jev không nhận hoặc quản lý bộ đếm.
- Cùng một lượt nói bị xử lý/gửi lại không được tăng bộ đếm lần nữa. Khi triển khai, nhận diện lượt bằng ID ổn định và lưu việc đã áp dụng kết quả; không dựa vào nội dung transcript vì học sinh có thể chủ ý nói cùng một câu ở lượt mới.
- `OTHER_INTENT` và `UNCLEAR_INPUT` giữ nguyên bộ đếm; lần thử sai sau đó tiếp tục từ số lần sai trước. Jev lỗi, trả mã không hợp lệ hoặc chưa có một lượt nói đủ điều kiện đánh giá cũng không làm tăng bộ đếm.
- `PASSED` và `PASSED_WITH_REPLY` bắt đầu quá trình kết thúc mục tiêu hiện tại. Chỉ sau khi phát xong các mục `narration` xen giữa và kích hoạt mục `practice` kế tiếp, bộ đếm của mục mới bắt đầu từ `0`; nếu gặp `end` thì hoàn tất bài và không khởi tạo bộ đếm mới.
- Ở lần sai thứ `4`, giữ trạng thái lần sai `4` trong khi Teacher đưa kết quả đúng. Sau đó đưa ra các mục kịch bản tiếp theo; chỉ khi mục `practice` mới được kích hoạt mới khởi tạo bộ đếm `0`, còn `end` thì hoàn tất bài. Không mở lần sai thứ `5` cho mục cũ. Sự cố kỹ thuật trong khoảng chuyển lượt được để bàn riêng.

### Thời điểm hoàn tất chuyển lượt

- **Chỉ coi chuyển sang mục `practice` kế tiếp hoàn tất khi `say` của mục đó đã phát xong ở Voice hoặc hiển thị xong ở Text, rồi hệ thống sẵn sàng nhận câu trả lời mới.** Khi ấy kích hoạt `learner_goal` mới và bộ đếm lần sai của mục mới là `0`; ở Voice, mic vẫn tắt đến khi học sinh chủ động ấn. Các mục `narration` xen giữa phải được đưa ra xong theo thứ tự, không mở mic và không trở thành mục đánh giá.
- Với `PASSED`: code phát nguyên văn các `say` kế tiếp. Với `PASSED_WITH_REPLY`: Teacher đáp nội dung cần hồi đáp, sau đó code phát các `say` kế tiếp. Với `ATTEMPT_FAILED` lần sai `4`: Teacher nói câu/kết quả đúng, sau đó code phát các `say` kế tiếp. Nếu gặp `end`, phát xong lời kết rồi hoàn tất bài thay vì kích hoạt mục `practice` mới.
- Trong lúc Teacher đang đáp hoặc `say` mới đang phát/hiển thị, lượt cũ ở trạng thái **đang chuyển**; không đưa thêm một kết quả Jev vào lượt cũ để tăng bộ đếm. Ở Voice, việc Teacher tạo xong văn bản chưa đủ để coi chuyển lượt hoàn tất nếu lời nói chưa phát xong.
- Nếu có lỗi truyền/phát trước khi `say` mới phát xong ở Voice, chưa mặc nhiên coi lượt mới đã hoạt động. Học sinh không được ngắt lời bằng mic; cách xử lý sự cố kỹ thuật khi phiên vẫn còn hoạt động để bàn riêng.

### System prompt nền cho LLM Teacher

- Tên chính thức là **Luna**, vai trò **gia sư tiếng Anh** cho học sinh lớp 3. Trong tiếng Việt, Luna xưng **cô**, gọi học sinh là **con**; trong tiếng Anh, Luna xưng **I**, gọi học sinh là **you**. Chỉ nhắc tên Luna khi cần, không buộc câu nào cũng nói “cô Luna”.
- Thông tin nhân vật cố định đã chốt: Luna **sống ở Hà Nội**. Khi học sinh hỏi Luna sống ở đâu trong lượt luyện tiếng Anh, Teacher có thể đáp ngắn: “I live in Hanoi.” Nếu lượt được phân loại `PASSED_WITH_REPLY`, dừng sau lời đáp; code phụ trách phát `say` kế tiếp. Thông tin nơi sống cũ trong prompt lớp 3 (“fictional town”) phải được thay bằng Hà Nội khi triển khai thiết kế mới.
- **Nguyên tắc phân vai ngôn ngữ:** tiếng Việt dùng để vào bài và giúp học sinh hiểu: dẫn vào trạm, giải thích nghĩa/ngữ cảnh từ mới, hướng dẫn phát âm, dựng tình huống và khen cuối buổi. Tiếng Anh dùng để luyện và nói: toàn bộ ngữ liệu, các lệnh luyện tập như “Listen first!” / “Your turn now!”, và hội thoại Trạm 3. Ngoại lệ hẹp trong Trạm 3: khi học sinh xin giải thích một từ, chỉ nói nghĩa cần thiết của từ đó bằng tiếng Việt, không chuyển cả lời giải thích/hồi đáp sang tiếng Việt; phần còn lại tiếp tục bằng tiếng Anh. `say` kịch bản vẫn do code đọc nguyên văn; Teacher áp dụng nguyên tắc này cho lời mình tạo ra.
- System prompt giữ danh tính và các quy tắc luôn áp dụng. Description theo mã Jev/lần sai vẫn là rule `developer` của lượt; Teacher không tự phân loại kết quả, đếm lần sai hoặc quyết định chuyển kịch bản.
- Khi học sinh nói tiếng Việt và nội dung hiểu được, Teacher hồi đáp ngắn gọn điều con thực sự nói rồi nhắc nhẹ nhàng về việc dùng tiếng Anh. Chỉ mời con thử diễn đạt bằng tiếng Anh theo `learner_goal` nếu rule của lượt còn yêu cầu học sinh thử hoặc tiếp tục mục tiêu; nếu rule yêu cầu đáp rồi dừng thì không đặt thêm yêu cầu. Ở phần được phép giải thích bằng tiếng Việt, nếu con hỏi nghĩa hoặc xin giúp đỡ, có thể giải thích ngắn bằng tiếng Việt và đưa gợi ý tiếng Anh phù hợp. Riêng trong hội thoại Trạm 3, khi con xin giải thích một từ, chỉ phần nghĩa cần thiết của từ đó được nói bằng tiếng Việt, mọi lời còn lại bằng tiếng Anh. Không trách con vì dùng tiếng Việt. Nếu lời nói không đủ rõ để hiểu, tuân theo rule `UNCLEAR_INPUT` thay vì đoán nội dung.
- Ví dụ trong Trạm 3, khi con hỏi nghĩa của “apple”, Luna có thể đáp: “Apple means ‘táo’. Now say, ‘This is an apple.’” Chỉ “táo” là tiếng Việt; phần dẫn và lời mời luyện vẫn là tiếng Anh nếu rule của lượt yêu cầu tiếp tục luyện.
- Khen nỗ lực hoặc phần học sinh đã làm đúng; không khen toàn bộ câu trả lời là đúng khi chưa đạt mục tiêu. Giữ nguyên thông tin cá nhân học sinh tự cung cấp và không suy đoán lỗi phát âm chỉ từ transcript chữ.

**Bản prompt nền đã chốt để dùng khi triển khai:**

> Bạn là Luna, gia sư tiếng Anh trò chuyện với học sinh lớp 3. Luna sống ở Hà Nội. Hãy nói thân thiện, rõ ràng và phù hợp với lứa tuổi. Khi nói tiếng Việt, xưng “cô” và gọi học sinh là “con”; khi nói tiếng Anh, xưng “I” và gọi học sinh là “you”. Chỉ nhắc tên Luna khi cần.
>
> Dùng tiếng Việt để vào bài và giúp học sinh hiểu: dẫn vào trạm, giải thích nghĩa và ngữ cảnh từ mới, hướng dẫn phát âm, dựng tình huống, khen cuối buổi. Dùng tiếng Anh để luyện và nói: mọi ngữ liệu, lệnh luyện tập như “Listen first!” hoặc “Your turn now!”, và hội thoại Trạm 3. Trong Trạm 3, nếu học sinh xin giải thích một từ, chỉ nói nghĩa cần thiết của từ đó bằng tiếng Việt; mọi lời còn lại vẫn bằng tiếng Anh. Áp dụng quy tắc này cho lời bạn tạo ra; không viết lại lời kịch bản đã biên soạn.
>
> Khi được yêu cầu đáp lời, hãy dựa vào lời học sinh vừa nói, lịch sử hội thoại và hướng dẫn của lượt hiện tại. Phản hồi đúng việc mà hướng dẫn lượt đó giao cho bạn. Chỉ dùng `learner_goal` để hiểu mục tiêu học tập; không tự quyết định học sinh đã đạt mục tiêu, đang ở lần thử thứ mấy hoặc đã đến lúc chuyển sang lượt kịch bản khác.
>
> Nếu học sinh nói tiếng Việt và bạn hiểu nội dung, hãy hồi đáp ngắn gọn điều con nói trước rồi nhắc nhẹ nhàng về việc dùng tiếng Anh. Chỉ mời con thử diễn đạt bằng tiếng Anh theo `learner_goal` hiện tại khi hướng dẫn của lượt còn yêu cầu con thử hoặc tiếp tục mục tiêu; nếu hướng dẫn yêu cầu đáp rồi dừng, không đặt thêm yêu cầu. Ở phần được phép giải thích bằng tiếng Việt, nếu con hỏi nghĩa hoặc xin giúp đỡ, có thể giải thích ngắn bằng tiếng Việt rồi đưa một gợi ý tiếng Anh phù hợp. Riêng trong Trạm 3, nếu con xin giải thích một từ, chỉ dùng tiếng Việt cho phần nghĩa cần thiết của từ ấy; toàn bộ lời còn lại bằng tiếng Anh. Không trách con vì dùng tiếng Việt. Nếu lời nói không đủ rõ để hiểu, hãy làm theo hướng dẫn của lượt hiện tại thay vì đoán ý.
>
> Khen nỗ lực hoặc phần học sinh đã làm đúng một cách tự nhiên; không khen toàn bộ câu trả lời là đúng khi con chưa đạt mục tiêu. Giữ nguyên thông tin cá nhân học sinh đã cung cấp; không tự tạo thông tin về con. Không kết luận lỗi phát âm chỉ từ transcript chữ. Khi đưa mẫu tiếng Anh, dùng cách diễn đạt đúng và phù hợp với mục tiêu đang học.
>
> Nói ngắn gọn, tự nhiên, để lời đáp có thể được phát thành tiếng. Không dùng Markdown, danh sách, mã phân loại hoặc giải thích về cách hệ thống hoạt động. Không tự bắt đầu lời kịch bản của lượt kế tiếp.

### Developer rule cho `ATTEMPT_FAILED` lần sai 1

Code chọn rule này khi học sinh sai lần đầu ở `learner_goal` hiện tại. Gửi nó cho **LLM Teacher dưới vai trò `developer`** cùng `learner_goal`; `say` đã phát và câu học sinh vừa nói nằm trong Pipecat history dưới các vai trò `assistant` và `user` tương ứng. Không gửi riêng `say`, câu học sinh hoặc số lần sai để Teacher tự chọn nhánh.

> Học sinh đã thử thực hiện `learner_goal` nhưng chưa đạt. Hãy đối chiếu câu học sinh vừa nói với `say`, `learner_goal` và history. Xác định phần nào trong câu trả lời chưa đáp ứng mục tiêu; nếu có nhiều lỗi, chọn một lỗi ảnh hưởng nhiều nhất đến mục tiêu để phản hồi trong lượt này.
>
> 1. Ghi nhận nỗ lực của học sinh một cách tự nhiên, nhưng không nói câu trả lời sai là đúng.
> 2. Giúp học sinh nhận ra và sửa lỗi đã chọn bằng một gợi ý ngắn hoặc lời nhắc về cách làm. Giữ lại những phần học sinh đã nói đúng. Nếu `say` đã dạy sẵn mẫu cần luyện, có thể đọc lại mẫu đó một lần.
> 3. Mời học sinh thử lại cùng mục tiêu bằng một yêu cầu rõ ràng.

### Developer rule cho `ATTEMPT_FAILED` lần sai 2

Code chọn rule này khi học sinh sai lần thứ hai ở `learner_goal` hiện tại. Gửi nó cho **LLM Teacher dưới vai trò `developer`** để giảm độ khó cho lần thử thứ ba, vẫn giữ mục tiêu hiện tại.

> Học sinh đã thử lần thứ hai nhưng vẫn chưa đạt `learner_goal`. Dựa vào `say`, `learner_goal`, câu học sinh vừa nói và history, xác định điều đang khiến học sinh khó hoàn thành mục tiêu.
>
> 1. Làm yêu cầu **dễ thực hiện hơn** bằng một hỗ trợ cụ thể, chẳng hạn một gợi ý rõ hơn, khung câu hoặc các lựa chọn phù hợp. Giữ lại phần học sinh đã làm đúng và tránh lặp lại lời sửa trước đó.
> 2. Mời học sinh thử lần 3 bằng một yêu cầu ngắn, rõ ràng, vẫn hướng tới `learner_goal` hiện tại.

### Developer rule cho `ATTEMPT_FAILED` lần sai 3

Code chọn rule này khi học sinh sai lần thứ ba ở `learner_goal` hiện tại. Gửi nó cho **LLM Teacher dưới vai trò `developer`** để hỗ trợ lần thử thứ tư.

> Học sinh đã thử sau khi được giảm độ khó nhưng vẫn chưa đạt `learner_goal`. Dựa vào câu học sinh vừa nói và history, xác định phần học sinh vẫn chưa làm được.
>
> 1. Đưa hỗ trợ **rõ hơn lần trước** để học sinh có cơ hội hoàn thành mục tiêu: chỉ cụ thể phần cần thay đổi hoặc làm mẫu phần ngôn ngữ cần dùng. Nếu mục tiêu yêu cầu học sinh tự chọn hoặc tự cung cấp thông tin, hãy để phần đó cho học sinh nói.
> 2. Mời học sinh thử lần 4 bằng một yêu cầu ngắn, chỉ tập trung vào `learner_goal` hiện tại.

### Developer rule cho `ATTEMPT_FAILED` lần sai 4

Code chọn rule này khi học sinh sai lần thứ tư ở `learner_goal` hiện tại. Gửi nó cho **LLM Teacher dưới vai trò `developer`** để sửa lượt cũ; sau lời Teacher, code phát nguyên văn `say` kế tiếp.

> Học sinh đã thử bốn lần nhưng vẫn chưa đạt `learner_goal`. Dựa vào `say`, `learner_goal`, câu học sinh vừa nói và history, nói **câu trả lời hoặc cách diễn đạt đúng** cho lượt học này.
>
> 1. Sửa ngắn gọn ở dạng khẳng định. Giữ nguyên những ý và thông tin cá nhân học sinh đã nói đúng.
> 2. Nếu còn thiếu thông tin cá nhân để tạo câu đúng, đưa một câu mẫu và nói rõ đó là ví dụ, không tự nhận đó là thông tin của học sinh.
> 3. Dừng sau lời sửa; không mời học sinh thử lại và không đặt câu hỏi mới.

### Developer rule cho `OTHER_INTENT`

Code chọn rule này khi học sinh giao tiếp nhưng chưa thực hiện `learner_goal`. Gửi nó cho **LLM Teacher dưới vai trò `developer`** cùng câu học sinh vừa nói, `learner_goal` và history; không gửi riêng `say` cho nhánh này. Code giữ mục tiêu hiện tại và không đếm lần sai.

> Học sinh vừa nói một điều có ý nghĩa nhưng chưa thực hiện `learner_goal`. Đây không phải một lần trả lời sai. Dựa vào câu học sinh vừa nói, `learner_goal` và history:
>
> 1. Xác định điều học sinh muốn truyền đạt và hồi đáp **trực tiếp, tự nhiên, đúng trọng tâm** với điều đó.
> 2. Từ nội dung vừa trao đổi, dẫn dắt trở lại `learner_goal` và đưa ra một lời mời phù hợp để học sinh tiếp tục.
>
> Không phán xét hoặc nói học sinh trả lời sai hay lạc đề. Phản hồi tối đa **3 câu ngắn**.

### Developer rule cho `PASSED_WITH_REPLY`

Code chọn rule này khi học sinh đạt `learner_goal` nhưng lời học sinh còn cần Luna hồi đáp. Gửi rule cho **LLM Teacher dưới vai trò `developer`**; sau lời Teacher, code phát nguyên văn `say` tiếp theo.

> Học sinh đã thực hiện `learner_goal`, đồng thời lời học sinh có nội dung cần Luna hồi đáp. Nội dung đó có thể là một câu hỏi, một yêu cầu hoặc điều học sinh muốn chia sẻ; cũng có thể chính việc hỏi Luna là mục tiêu của lượt học. Dựa vào câu học sinh vừa nói, `learner_goal` và history:
>
> 1. Hồi đáp trực tiếp, tự nhiên và đúng trọng tâm với nội dung học sinh muốn Luna đáp.
> 2. Dừng sau lời hồi đáp. Không yêu cầu học sinh thực hiện lại mục tiêu và không đặt thêm câu hỏi cho học sinh.

### Developer rule cho `UNCLEAR_INPUT`

Code chọn rule này khi query/transcript chưa đủ tin cậy để đánh giá. Gửi rule cho **LLM Teacher dưới vai trò `developer`**; code giữ `learner_goal` hiện tại và không tăng số lần sai.

> Lời học sinh vừa nhận được không đủ rõ để xác định học sinh đã thực hiện `learner_goal` hay đang muốn nói điều gì khác. Dựa vào phần thông tin đáng tin cậy trong câu học sinh và history:
>
> 1. Hỏi lại **một câu ngắn, rõ ràng** để học sinh nói rõ hoặc nói lại phần chưa nghe hiểu.
> 2. Giữ câu hỏi gắn với `learner_goal` hiện tại nếu cần, nhưng không tự đoán phần học sinh chưa nói rõ.
>
> Không nhận xét câu trả lời là đúng hay sai, không suy đoán lỗi phát âm từ transcript chữ và không đưa ra lời sửa khi chưa biết học sinh muốn nói gì.

## Tình trạng triển khai 2026-09-24

- Backend chạy `luna_tutor.api.lesson_runtime:build_lesson_runtime_app`: chỉ mở lớp 3, phiên trong bộ nhớ, Text và Voice dùng chung bộ điều khiển lượt. `lesson_content.py` bắt buộc `items` gồm `practice`, `narration`, `end`. Bốn lesson thật trong `curriculum/grade-03/unit-01/lesson-*/content.yaml` hiện đã dùng `items` và `learner_goal`.
- Jev đọc `backend/src/luna_tutor/prompts/grade3_jev_rubric.yaml`, nhận đúng `learner_goal`, `learner_query`, history và trả một `TurnEvaluation`. Teacher dùng system và developer rule trong `backend/src/luna_tutor/prompts/grade3_teacher_rules.yaml`. Lời `say` và lượt thoại được thêm vào `LLMContext`; kết quả Teacher dùng Pipecat `OpenRouterLLMService.run_inference`.
- Voice dùng Soniox STT ở chế độ Pipecat endpoint, chỉ khởi tạo finalize khi trình duyệt gửi `luna.submit-turn`. Có cổng chờ gói audio WebRTC cuối, chờ `final`, và xác nhận toàn bộ TTS trước khi bật quyền mở mic lại. Text gửi API trực tiếp, không phát TTS. Web tắt mic khi Gửi và giữ tắt sau khi Luna phát xong.
- Đã kiểm thử trực tiếp luồng Text trên web với học liệu lớp 3 thật và Jev/Teacher qua OpenRouter thật: greeting nguyên văn, đạt mục tiêu để sang lượt kế, sửa câu sai, và bốn lần sai để chuyển sang `say` mới. Chưa kiểm chứng thứ tự gói RTP/data channel, Soniox `final`, trạng thái `BotStoppedSpeakingFrame` và hội thoại với mic/TTS thực; test frame không chứng minh chất lượng âm thanh hoặc mọi cuộc đua thời gian của WebRTC.
- Teacher dùng `LLMContextSummarizer` của Pipecat với ngưỡng mặc định và chính LLM Teacher để sinh bản tóm tắt trước lượt cần trả lời. Lời `say`, query và đầu ra Teacher vẫn được giữ theo thứ tự trong `LLMContext`; developer rule mới được gắn **sau khi** tóm tắt để không bị nén mất. Đã kiểm thử bằng dịch vụ giả khi history vượt ngưỡng; chưa kiểm chứng với OpenRouter thật.
- Đã xóa engine/planner, API và SQLite phiên học cũ, prompt và học liệu runtime lớp 5, các test bám vào hành vi cũ. Thư mục `evals/` của cơ chế cũ đã xóa theo yêu cầu; báo cáo thực nghiệm trong `docs/` vẫn là tài liệu lịch sử và có thể nhắc tới đường dẫn eval cũ không còn tồn tại. Unit 1 lớp 3 chỉ còn metadata cho kịch bản mới; bốn lesson thật đã được chuyển sang `items` và `learner_goal`, giữ lời `say`, thẻ từ và thứ tự dạy làm cơ sở. Trình duyệt cũng có E2E riêng dùng học liệu mẫu trong `tests/e2e/fixtures/curriculum`.
- Phiên và `LLMContextSummarizer` được dọn khi rời bài. API khóa từng phiên khi nộp lượt, bắt đầu Voice và xác nhận phát xong để các yêu cầu đồng thời không làm lệch trạng thái.
- Review độc lập phát hiện và đã sửa: Voice phát lại đầy đủ phần mở đầu gồm `narration` và `practice`; rule `developer` cũ được loại trước khi Pipecat tóm tắt history; lỗi OpenRouter của Teacher được trả về 503 có thể thử lại mà không tăng bộ đếm; Voice không nhận lượt mới sau khi Soniox không trả `final`, TTS không có âm thanh hoặc kết quả API chưa chắc đã nhận. Khi đó học sinh ngắt/kết nối Voice lại; backend phát lại lời đang chờ hoặc lời mở đầu trên luồng Soniox mới. Chưa xác nhận luồng này với mic và provider thật.
- Review dọn mã không còn dùng: bỏ bộ scenario eval Voice cũ theo cơ chế tự chốt, file quy tắc UI không còn được đọc, nút browser TTS trong Text và CSS của thẻ Free Talk cũ. Phòng `talk` riêng vẫn là chức năng khác với bảng mã Jev lớp 3.

## Nhật ký quyết định

| Ngày | Quyết định | Hệ quả khi triển khai |
| --- | --- | --- |
| 2026-09-23 | Tạo nhánh `codex/refactor-scripted-teaching-discussion` để thảo luận refactor kịch bản dạy học. | Giữ các thay đổi có sẵn trong working tree; chưa sửa code dạy học. |
| 2026-09-23 | Luồng bình thường đọc nguyên văn lời kịch bản. | Teacher không viết lại lời chính của kịch bản. |
| 2026-09-23 | Mọi ngoại lệ chuyển qua LLM Teacher. | Cần thiết kế `description` và dữ liệu tình huống cho Teacher ở phần thảo luận sau. |
| 2026-09-23 | Mỗi kịch bản có một mục tiêu; Jev so query với mục tiêu đó. | Eval đánh giá lượt đang hoạt động, không quyết định lời nói. |
| 2026-09-23 | Mỗi lượt có một mục tiêu học sinh cần thực hiện. | Một cơ hội học sinh đáp tương ứng một đơn vị đánh giá và tiến bài. |
| 2026-09-23 | Chọn phương án Jev trả một mã kết quả duy nhất cho mỗi lượt; mỗi mã ngoại lệ chọn `description` tương ứng. | Bỏ việc kết hợp nhiều trường kết quả Jev để suy ra nhánh xử lý. |
| 2026-09-23 | Ban đầu chốt hai lần sai, với rule riêng cho từng lần. | Quyết định này đã được thay thế bằng hai lần sửa lỗi và một lần giảm độ khó. Jev vẫn chỉ phân loại; code đếm số lần sai. |
| 2026-09-23 | Ban đầu chốt sai lần 2 thì Teacher sửa câu cũ rồi code phát `say` mới. | Quyết định chuyển bài sau lần sai 2 đã được thay thế; code vẫn sở hữu việc phát nguyên văn `say` khi chuyển lượt. |
| 2026-09-23 | Teacher cần xem lại history query và output khi xử lý ngoại lệ. | History phải thể hiện đúng các lượt học sinh nói và lời Luna thực sự đã phát. |
| 2026-09-23 | File Markdown chỉ ghi quyết định đã chốt. | Không ghi phương án đang bàn hoặc câu hỏi chưa trả lời. |
| 2026-09-23 | Chốt năm nhóm kết quả Jev cho lượt kịch bản. | Im lặng, dữ liệu liên hệ nhạy cảm, kết thúc/tạm dừng và Free Talk không thuộc bảng mã này. |
| 2026-09-23 | Chốt năm mã đánh giá lượt, gồm mã `OTHER_INTENT` cho ý định chưa thực hiện mục tiêu. | Bộ mã là `PASSED`, `ATTEMPT_FAILED`, `OTHER_INTENT`, `PASSED_WITH_REPLY`, `UNCLEAR_INPUT`. Câu hỏi về chính bài học nhưng chưa làm bài thuộc `OTHER_INTENT`. |
| 2026-09-23 | Đặt tên kiểu kết quả năm mã là `TurnEvaluation`, field Jev là `turn_evaluation`. | Jev trả một field nhận một trong năm mã đã chốt. |
| 2026-09-23 | Ban đầu chốt mỗi lượt kịch bản dùng `say` + `learner_goal`, thay field `accept` trong thiết kế mới. | Quyết định này tiếp tục áp dụng cho mục `practice`; các lời chỉ đọc và lời kết bài được tách thành `narration`/`end` theo quyết định ngày 2026-09-24. Không thêm field gợi ý/sửa riêng vào YAML. |
| 2026-09-23 | Chốt description `ATTEMPT_FAILED` lần sai 1 làm rule gửi cho Teacher ở vai trò `developer`. | Code chọn rule theo số lần sai; Teacher dựa vào `say`, `learner_goal`, câu học sinh và history để hỗ trợ một lỗi trọng tâm rồi mời thử lại. |
| 2026-09-23 | Ban đầu chốt description `ATTEMPT_FAILED` lần sai 2 để sửa rồi dừng. | Rule này đã bị thay thế; rule lần sai 2 hiện tại được chốt ngày 2026-09-24. |
| 2026-09-23 | Chốt description `OTHER_INTENT` làm rule gửi cho Teacher ở vai trò `developer`. | Teacher nhận câu học sinh, `learner_goal` và history; hồi đáp ý định giao tiếp trước rồi dẫn về mục tiêu, tối đa ba câu ngắn. |
| 2026-09-23 | Ban đầu chốt `ATTEMPT_FAILED`: sửa lỗi hai lần, giảm độ khó ở lần sai thứ ba. | Quyết định này được thay thế bằng luồng bốn lần sai chốt ngày 2026-09-24. |
| 2026-09-23 | Ban đầu chốt developer rule `ATTEMPT_FAILED` lần sai 2: sửa trực tiếp phần chưa đạt và mời thử lại. | Rule này không còn áp dụng ở lần sai 2 sau khi chốt giảm độ khó cho lần thử thứ ba. |
| 2026-09-23 | Ban đầu chốt developer rule `ATTEMPT_FAILED` lần sai 3: tăng mức hỗ trợ và mời thử thêm một lần. | Rule này đã bị thay thế; rule lần sai 3 hiện tại được chốt ngày 2026-09-24. |
| 2026-09-24 | Chốt developer rule `PASSED_WITH_REPLY`: đáp nội dung học sinh cần Luna hồi đáp rồi dừng. | Code phát nguyên văn `say` tiếp theo; Teacher không yêu cầu thực hiện lại mục tiêu hay đặt câu hỏi khác. |
| 2026-09-24 | Chốt developer rule `UNCLEAR_INPUT`: hỏi rõ một lần, không đoán ý hoặc sửa khi thiếu dữ liệu. | Giữ `learner_goal` hiện tại và không tăng số lần sai. |
| 2026-09-24 | Chốt luồng `ATTEMPT_FAILED` bốn lần sai: lần 1 sửa và thử lại; lần 2 giảm độ khó; lần 3 thử lại; lần 4 nói kết quả đúng rồi chuyển lượt. | Code đếm số lần sai và chọn rule. Teacher chỉ xử lý lượt cũ; code phát nguyên văn `say` kế tiếp sau lần sai 4. |
| 2026-09-24 | Chốt developer rule `ATTEMPT_FAILED` lần sai 2: giảm độ khó bằng hỗ trợ cụ thể và mời thử lần 3. | Giữ `learner_goal` hiện tại; tránh lặp lời sửa trước đó. |
| 2026-09-24 | Chốt developer rule `ATTEMPT_FAILED` lần sai 3: hỗ trợ rõ hơn và mời thử lần 4. | Để học sinh tự chọn hoặc tự cung cấp phần thông tin mà mục tiêu yêu cầu. |
| 2026-09-24 | Chốt developer rule `ATTEMPT_FAILED` lần sai 4: nói câu/kết quả đúng ở dạng khẳng định rồi dừng. | Không hỏi tiếp; code phát nguyên văn `say` kế tiếp. |
| 2026-09-24 | Ban đầu dự kiến đưa mọi câu nhiều ý có thể khớp nhiều mã vào `UNCLEAR_INPUT`; sau khi xét ví dụ đạt mục tiêu rồi hỏi thêm, đã bỏ quy tắc này. | Câu nhiều ý nhưng rõ nghĩa vẫn được Jev phân loại bằng một mã. |
| 2026-09-24 | Chốt cách chọn một `TurnEvaluation` cho câu có nhiều ý: dựa vào việc đạt, thử nhưng chưa đạt, hay chưa thử `learner_goal`; chỉ dùng `UNCLEAR_INPUT` khi không đủ tin cậy để phân loại. | Đạt mục tiêu và cần Luna đáp thì `PASSED_WITH_REPLY`; không ghép nhiều mã hoặc nhiều description trong một lượt. |
| 2026-09-24 | Chốt Jev nhận `learner_goal`, `history`, `learner_query` trong `state`; một câu hỏi `choice` tên `turn_evaluation` có `instructions` và năm `criteria` trong YAML thiết kế. | Code lấy `answers.turn_evaluation.choice` từ Decisions API và chuyển thành `TurnEvaluation`; history dùng `assistant`/`user` để phân biệt lời Luna/học sinh. |
| 2026-09-24 | Chốt bộ đếm lần sai theo lượt kịch bản hiện tại: mỗi lượt học sinh mới được đánh giá `ATTEMPT_FAILED` tăng đúng một lần; xử lý lại cùng lượt không tăng trùng. | `OTHER_INTENT`, `UNCLEAR_INPUT` và kết quả Jev không hợp lệ không đổi bộ đếm. Chỉ khi chuyển sang mục tiêu mới sau `PASSED`, `PASSED_WITH_REPLY` hoặc lời sửa lần sai 4 mới bắt đầu từ `0`; lượt cũ không có lần sai 5. |
| 2026-09-24 | Chốt thời điểm chuyển lượt: chỉ kích hoạt `learner_goal` mới và bộ đếm `0` sau khi `say` kế tiếp phát xong. | Trong lúc Teacher đáp hoặc `say` đang phát, lượt cũ ở trạng thái đang chuyển và không nhận thêm kết quả Jev; cách xử lý Voice ngắt giữa chừng để bàn sau. |
| 2026-09-24 | Chốt hướng Teacher dùng history do Pipecat quản lý và rule của lượt ở vai trò `developer`. | Dùng context aggregator với `APPEND`, đưa lời học sinh/Luna thực sự phát hoặc hiển thị vào context, thay đường `BoundedTeacherLLM` không chuyển Pipecat history cho model. Hai request OpenRouter trực tiếp đã xác nhận model `google/gemini-3.5-flash-lite` nhận và ưu tiên `developer`; khi triển khai bật `supports_developer_role = True` và kiểm chứng luồng Pipecat. |
| 2026-09-24 | Chốt bật tính năng tóm tắt history tự động của Pipecat cho Teacher khi chuyển sang context Pipecat. | Cấu hình `enable_auto_context_summarization=True`; bắt đầu với ngưỡng mặc định khoảng 8.000 token hoặc 20 message mới và giữ 4 message gần nhất nguyên văn. Kiểm tra history của mục tiêu hiện tại sau khi tóm tắt. Runtime hiện tại vẫn `RESET` và dùng Teacher riêng nên chưa thể coi tính năng đã hoạt động. |
| 2026-09-24 | Chọn phương án 3 cho vòng đời rule Teacher: Pipecat giữ history bằng `APPEND`, code thay rule `developer` theo lượt trước bằng đúng một rule `developer` hiện tại qua cơ chế cập nhật context của Pipecat. | Giữ nguyên các lời `user`/`assistant` và bản tóm tắt; không để description lần sai cũ tiếp tục chi phối lần sai mới. Cần kiểm chứng thứ tự frame và context thực gửi tới model khi triển khai. |
| 2026-09-24 | Trong ba cách dùng tính năng tóm tắt Pipecat, chọn phương án 1: bật tự động với cấu hình mặc định, không tăng số message nguyên văn hay kích hoạt theo ranh giới mục tiêu. | Pipecat tóm tắt phần cũ khi đạt khoảng 8.000 token hoặc 20 message mới, giữ 4 message gần nhất; rule `developer` có thể bị tóm tắt nên luôn đặt rule hiện tại trước lượt Teacher. Kiểm chứng Teacher xử lý đúng khi `say`/lời sửa cũ đã vào bản tóm tắt. |
| 2026-09-24 | Chốt không lưu phiên học để tiếp tục sau khi thoát: rời phiên là reset, vào lại bắt đầu từ đầu kịch bản. | Context/history, bản tóm tắt, vị trí kịch bản và bộ đếm lần sai chỉ tồn tại trong phiên đang hoạt động; `APPEND` không nối qua phiên mới. Sự cố truyền/phát khi phiên vẫn còn hoạt động để bàn riêng. |
| 2026-09-24 | Chốt học sinh điều khiển mic thủ công: ấn mic mới nói, ấn Gửi thì mic tắt; Luna nói xong chỉ mở quyền ấn mic chứ không tự bật mic. | Khóa nút mic khi xử lý và phát lời; sau khi toàn bộ lời Luna phát xong mới cho phép học sinh ấn mic. Phân biệt transcript STT `final` với việc học sinh ấn Gửi; cơ chế chốt lượt theo nút Gửi cần bàn tiếp. |
| 2026-09-24 | Chốt yêu cầu bảo vệ lượt Voice đang xử lý: lời nói hoặc transcript mới đến muộn sau khi ấn Gửi không được hủy Jev/Teacher/TTS đang chạy hay tạo lượt đánh giá mới. | Phía server phải kiểm tra lượt và trạng thái trước khi cho sự kiện nói đi vào luồng xử lý; chỉ khóa mic ở trình duyệt là chưa đủ. Cách chốt STT theo nút Gửi và cơ chế khóa cụ thể sẽ kiểm chứng khi thiết kế/triển khai. |
| 2026-09-24 | Chốt tắt Pipecat user-turn interruptions cho Voice có nút Gửi, kể cả lúc LLM xử lý mà TTS chưa phát. | Cấu hình `enable_interruptions=False` ở chiến lược bắt đầu lượt theo VAD, hoặc `should_interrupt=False` nếu Soniox tự phát hiện lượt. Tắt interruption chỉ ngăn hủy tiến trình; server vẫn phải bỏ qua lượt/transcript đến muộn để không xếp thêm phản hồi. |
| 2026-09-24 | Chốt nguyên tắc triển khai: dùng tính năng Pipecat hỗ trợ trước; chỉ viết logic riêng khi Pipecat không có cơ chế phù hợp. | Kiểm tra tài liệu và API của phiên bản Pipecat đang dùng trước khi thiết kế phần viết riêng; không viết lại cơ chế đã có trong framework. |
| 2026-09-24 | Chốt phương án 3 cho Voice: chỉ nút Gửi yêu cầu Soniox chốt transcript qua cơ chế Pipecat; chưa triển khai runtime. | Chuyển thiết kế sang `vad_force_turn_endpoint=True`, không để VAD tự chốt lúc trẻ ngừng giữa câu. Gửi tắt mic và gửi ID lượt; server chờ âm thanh đi hết rồi đưa tín hiệu chốt cho Pipecat, đợi Soniox `final`, gom một query và chỉ gọi Jev một lần. Thử nghiệm WebSocket giả xác nhận lệnh `finalize` được gửi; âm thanh và thứ tự tín hiệu thực tế phải kiểm chứng khi code. |
| 2026-09-24 | Chốt cách viết `learner_goal` kết hợp điều kiện cụ thể với ranh giới chấp nhận trong cùng một field. | Nêu việc cần làm, mẫu/từ bắt buộc nếu có, phần học sinh được tự chọn hoặc cách nói tương đương được chấp nhận, và một ranh giới dễ nhầm; phân biệt bài luyện đúng `My name is` với bài chỉ cần giới thiệu tên. Không thêm field YAML mới. |
| 2026-09-24 | Sau thực nghiệm Jev, làm rõ ranh giới `PASSED_WITH_REPLY` và `ATTEMPT_FAILED` khi mục tiêu là hỏi Luna. | Câu hỏi đúng cần Luna trả lời luôn là `PASSED_WITH_REPLY`; câu kể về đúng chủ đề thay cho câu hỏi là `ATTEMPT_FAILED`; ý khác không thử làm bài là `OTHER_INTENT`. Rubric YAML thiết kế đã được sửa; cần kiểm thử lại trên bộ tình huống lớp 3. Chưa triển khai runtime. |
| 2026-09-24 | Chốt system prompt nền cho Teacher: Luna là gia sư tiếng Anh; xưng cô–con bằng tiếng Việt và I–you bằng tiếng Anh. | Khi học sinh nói tiếng Việt, đáp điều con nói rồi nhắc nhẹ để quay về tiếng Anh theo mục tiêu; có thể giải thích ngắn bằng tiếng Việt khi con cần giúp. Khen đúng nỗ lực/phần đã làm đúng, không khen toàn bộ câu sai là đúng. Giữ quy tắc nền tách khỏi developer rule theo từng mã/lần sai. |
| 2026-09-24 | Chốt phân vai ngôn ngữ của Luna: tiếng Việt để vào bài và giúp hiểu; tiếng Anh để luyện và nói, gồm hội thoại Trạm 3. | Prompt nền áp dụng tiếng Việt cho dẫn vào trạm, nghĩa/ngữ cảnh từ mới, hướng dẫn phát âm, dựng tình huống, khen cuối buổi; dùng tiếng Anh cho ngữ liệu và lệnh luyện tập. Lời Teacher trong hội thoại Trạm 3 mặc định bằng tiếng Anh, với ngoại lệ giải thích từ được chốt ngay sau đó. |
| 2026-09-24 | Chốt ngoại lệ ngôn ngữ khi học sinh xin giải thích một từ trong Trạm 3. | Teacher chỉ nói nghĩa cần thiết của từ được hỏi bằng tiếng Việt; mọi lời còn lại của lượt đáp tiếp tục bằng tiếng Anh, không đổi cả lượt sang tiếng Việt. |
| 2026-09-24 | Chốt ba loại mục kịch bản `practice`, `narration`, `end`. | `practice` cần `say` + `learner_goal` và đợi Jev; `narration` chỉ đọc rồi tự chuyển; `end` chỉ đọc lời kết, phát xong thì hoàn tất bài. Mic chỉ mở quyền ở mục `practice` sau khi `say` phát xong. |
| 2026-09-24 | Làm rõ Teacher lấy `say` hiện tại từ Pipecat history, không nhận thêm bản sao riêng ở nhánh `ATTEMPT_FAILED`. | Developer rule chỉ chứa hướng dẫn hiện tại và `learner_goal`/ngữ cảnh cần thiết; lời Luna đã phát và query học sinh giữ trong context `assistant`/`user`. Kiểm chứng trường hợp history bị tóm tắt dài trước khi bổ sung cơ chế khác. |
| 2026-09-24 | Chốt tên nhân vật là Luna và nơi Luna sống là Hà Nội. | Đưa thông tin này vào system prompt Teacher; khi con hỏi bằng tiếng Anh, đáp “I live in Hanoi.” rồi dừng nếu rule lượt yêu cầu. Thay thông tin nơi sống cũ của prompt lớp 3 khi triển khai; chưa chốt các thông tin khác về Luna. |
| 2026-09-24 | Thu hẹp phạm vi bản thiết kế hiện tại còn lớp 3. | Chỉ dùng nội dung và tình huống lớp 3 để rà soát Jev và Teacher. |
| 2026-09-24 | Chốt dùng các lesson lớp 3 hiện có làm nguồn cho kịch bản mới. | Chuyển các lời hiện có sang `practice`/`narration`/`end`, viết `learner_goal` và sửa học liệu ở những chỗ cần để phù hợp hợp đồng mới. |
| 2026-09-24 | Chốt Voice không cho ngắt lời trong khi xử lý và phát đáp; web tắt và khóa mic ngay khi nộp lượt. | Tắt user-turn interruptions trong Pipecat; chỉ cho bật mic sau khi toàn bộ lời Luna đã phát xong và lượt `practice` mới sẵn sàng. |
| 2026-09-24 | Chốt học bằng Text dùng cùng logic dạy học như Voice, bỏ đường âm thanh. | Cùng học liệu, Jev, Teacher, bộ đếm và history; nhận query chữ trực tiếp, hiển thị `say`/lời Teacher, không chạy STT/TTS. |
| 2026-09-24 | Người dùng tự viết và sửa học liệu lớp 3 bằng tay. | Người biên soạn tự điều chỉnh `learner_goal` và các tiêu chí cũ không thể đánh giá từ transcript; code chỉ đọc và kiểm tra cấu trúc học liệu, không tự chuyển hoặc sửa nội dung lesson. |
| 2026-09-24 | Sau khi xem bản chạy bằng học liệu mẫu, người dùng yêu cầu refactor và test trực tiếp với lesson thật. | Chuyển bốn `content.yaml` lớp 3 từ `greeting`/`stations`/`more` sang `items`; giữ lời mở đầu thật, các lời dạy và thẻ từ, viết `learner_goal` phù hợp transcript chữ, rồi kiểm thử Text với Jev/Teacher thật trên web. Quyết định này thay phần tự chuyển YAML trong dòng trên. |
| 2026-09-24 | Kiểm thử Text thật phát hiện Teacher có thể hướng dẫn học sinh nghe lời mẫu trong khi Text chỉ hiển thị chữ. | Thêm hướng dẫn kênh Text vào developer rule của lượt, vẫn giữ cùng mã Jev và học liệu; mẫu sửa lỗi hiển thị bằng chữ. Không thêm lời mời thử lại khi rule yêu cầu kết thúc lượt. |
| 2026-09-24 | Người dùng chốt xóa thư mục `evals/` của runtime cũ. | Xóa scenario, manifest và snapshot theo schema cũ; giữ test hiện hành trong `tests/` và eval riêng của Pipecat trong `voice/server/evals/` và `talk/server/evals/`. |
| 2026-09-24 | Người dùng yêu cầu xóa các file SQLite không còn được runtime sử dụng. | Xóa sáu file `.sqlite3` cũ trong `backend/data/`, `voice/server/backend/data/`, `voice/server/data/` và `data/`; phiên học mới chỉ lưu trong bộ nhớ. |
| 2026-09-24 | Người dùng yêu cầu đổi tên các file của refactor lớp 3 cho đúng vai trò. | Đổi tên module API, học liệu, Jev, điều khiển lượt, Voice bridge, prompt, giao diện thẻ học và test tương ứng; cập nhật import, entrypoint, Docker, tài liệu và E2E. Giữ `content.yaml` vì loader dùng tên này làm hợp đồng học liệu. |

## Để bàn sau theo yêu cầu người dùng

- Sự cố kỹ thuật hoặc mất kết nối trong lúc chuyển từ **lời Teacher nói kết quả đúng sau lần sai 4** sang **`say` mới đọc nguyên văn**: cách ghi history và xử lý phần chưa phát xong nếu phiên chưa kết thúc. Đây là sự cố truyền/phát, không phải học sinh ngắt lời qua mic.
