# 50 tình huống học sinh lớp 3 nói, khác cả ý nghĩa

Ngày tạo: 2026-09-23; cập nhật phạm vi lớp 3: 2026-09-24. Đây là **bộ ví dụ thiết kế**, chưa phải kết quả Jev thật hoặc test tự động. Mỗi hàng minh họa một tình huống hoặc ranh giới ý nghĩa khác nhau, không chỉ đổi từ, dịch ngôn ngữ hoặc thay tên trong cùng một câu. `learner_goal` được viết ngắn để làm rõ việc học sinh cần thực hiện ở lượt kịch bản; đây là ngữ cảnh mẫu, không thay thế YAML production.

Mọi transcript trong bảng là `final`, trừ ba hàng `UNCLEAR_INPUT` được ghi rõ `uncertain`. Bộ này không gồm im lặng, thông tin liên hệ nhạy cảm, lệnh kết thúc/tạm dừng hoặc Free Talk. Năm mã kỳ vọng theo [quyết định refactor](../grade3_lesson_refactor_spec.md).

## `PASSED` — đạt mục tiêu, không có nhu cầu khác

| # | Lớp | `learner_goal` của lượt hiện tại | Ý nghĩa riêng của lời học sinh | Học sinh nói |
| ---: | --- | --- | --- | --- |
| 01 | 3 | Chào cô bằng `Hi` hoặc `Hello`. | Chào Luna. | “Hello, Luna!” |
| 02 | 3 | Tự giới thiệu tên bằng tiếng Anh. | Cho biết tên mình là An. | “My name is An.” |
| 03 | 3 | Nói hôm nay mình cảm thấy thế nào. | Bày tỏ sự hào hứng. | “I'm excited today!” |
| 04 | 3 | Nói lời tạm biệt và hẹn gặp lại. | Hẹn gặp lại ngày mai. | “See you tomorrow!” |
| 05 | 3 | Nói lời chào buổi sáng. | Chào vào buổi sáng. | “Good morning!” |
| 06 | 3 | Nói lời chào khi gặp buổi tối bằng `Good evening`. | Chào Luna đầu buổi tối. | “Good evening, Luna.” |
| 07 | 3 | Đáp lời giới thiệu của Tom bằng `Nice to meet you`. | Bày tỏ vui được làm quen. | “Nice to meet you, Tom.” |
| 08 | 3 | Nói lời cảm ơn bằng tiếng Anh. | Cảm ơn vì vừa được giúp. | “Thank you!” |
| 09 | 3 | Nói `Good night` khi chia tay trước lúc ngủ. | Chúc bố mẹ ngủ ngon. | “Good night, Mum and Dad.” |
| 10 | 3 | Chào bạn lúc mới gặp vào buổi chiều bằng `Good afternoon`. | Chào lúc đầu buổi chiều. | “Good afternoon, Ben.” |

## `ATTEMPT_FAILED` — đã thử trả lời nhưng không đạt `learner_goal`

| # | Lớp | `learner_goal` của lượt hiện tại | Ý nghĩa riêng của lời học sinh / điểm chưa đạt | Học sinh nói |
| ---: | --- | --- | --- | --- |
| 11 | 3 | Nói từ `hello`. | Có thử nói từ cần học nhưng thiếu phần cuối. | “Hel...” |
| 12 | 3 | Chào bạn bằng `Hi` trước, rồi chào Luna buổi tối bằng `Good evening`. | Gán lời chào buổi tối cho bạn và lời chào thân mật cho Luna. | “Good evening, Ben. Hi, Luna!” |
| 13 | 3 | Tự giới thiệu bằng `I'm` và một tên. | Mô tả mình là bạn của cô, không cho biết tên. | “I'm your friend.” |
| 14 | 3 | Giới thiệu tên bằng đúng mẫu `My name is [tên]`. | Nêu tên nhưng dùng `are` thay cho `is`. | “My name are Mai.” |
| 15 | 3 | Hỏi Luna `How are you?`. | Cố hỏi thăm nhưng thiếu chủ ngữ. | “How are?” |
| 16 | 3 | Trả lời `How are you?` bằng cảm xúc của **mình**. | Đưa ra cảm xúc của Tom thay cho bản thân. | “Tom is fine.” |
| 17 | 3 | Đáp lời `Nice to meet you` bằng câu gặp gỡ phù hợp. | Dùng lời tạm biệt khi vừa làm quen. | “Goodbye!” |
| 18 | 3 | Chào khi mới gặp vào buổi sáng. | Dùng lời chúc ngủ ngon sai thời điểm. | “Good night!” |
| 19 | 3 | Nói lời tạm biệt với bạn khi ra về. | Dùng lời chào mở đầu thay cho chia tay. | “Hello, Mai!” |
| 20 | 3 | Hẹn gặp **ngày mai** bằng `See you tomorrow`. | Hẹn gặp hôm nay thay vì ngày mai. | “See you today.” |
| 21 | 3 | Nói đủ cụm `Nice to meet you`. | Bắt đầu lời chào gặp mặt nhưng thiếu `you`. | “Nice to meet…” |
| 22 | 3 | Hỏi thăm Luna bằng câu hỏi tiếng Anh. | Dùng câu kể thay cho câu hỏi. | “You are fine.” |
| 23 | 3 | Trả lời `How are you?` bằng cảm xúc tiếng Anh. | Nói cảm xúc bằng tiếng Việt thay cho phần tiếng Anh cần luyện. | “Con thấy ổn ạ.” |
| 24 | 3 | Nói lời cảm ơn bằng `Thank you`. | Chỉ nói đại từ, chưa thể hiện lời cảm ơn. | “You.” |

## `OTHER_INTENT` — có ý định giao tiếp, chưa thử thực hiện `learner_goal`

| # | Lớp | `learner_goal` của lượt hiện tại | Ý nghĩa riêng của lời học sinh | Học sinh nói |
| ---: | --- | --- | --- | --- |
| 25 | 3 | Nói từ `hello`. | Hỏi nghĩa của từ sắp luyện. | “Hello nghĩa là gì ạ?” |
| 26 | 3 | Nói `Good evening`. | Hỏi thời điểm dùng lời chào đó. | “When do I say good evening?” |
| 27 | 3 | Nói `Goodbye`. | Hỏi cách đánh vần từ cần luyện. | “How do you spell goodbye?” |
| 28 | 3 | Trả lời cô đang cảm thấy thế nào. | Xin cô nhắc lại câu hỏi. | “Could you repeat the question?” |
| 29 | 3 | Nói `Nice to meet you`. | Xin cô nói chậm hơn. | “Please speak more slowly.” |
| 30 | 3 | Tự giới thiệu tên khi đổi vai. | Hỏi đang dùng tên mình hay tên nhân vật. | “Should I say my name or the character's name?” |
| 31 | 3 | Nói một tên trong câu giới thiệu. | Xin phép dùng tên giả. | “Can I use a made-up name?” |
| 32 | 3 | Chọn lời chào khi gặp hoặc chia tay. | Nói chưa hiểu sự khác nhau giữa hai tình huống. | “I don't know when to say hello or goodbye.” |
| 33 | 3 | Trả lời mình đang cảm thấy thế nào. | Không nhớ từ chỉ cảm xúc và xin gợi ý. | “Can you give me a word to start with?” |
| 34 | 3 | Tự giới thiệu tên. | Từ chối chia sẻ tên thật. | “I don't want to share my real name.” |
| 35 | 3 | Đọc cụm `Good evening`. | Bộc lộ sợ nói sai. | “I'm scared I'll say it wrong.” |
| 36 | 3 | Tạm biệt Luna. | Kể một tin vui không liên quan nhiệm vụ. | “I won a drawing prize today!” |
| 37 | 3 | Hỏi Luna `How are you?`. | Hỏi cô có phải người thật không. | “Luna, are you a real person?” |
| 38 | 3 | Đáp lại lời chào của Tom. | Phản đối vì Luna nghe nhầm câu vừa nói. | “I said hi, but you heard bye.” |
| 39 | 3 | Nói `Thank you`. | Xin cô giải thích bài bằng tiếng Việt. | “Can you explain this in Vietnamese?” |

## `PASSED_WITH_REPLY` — đạt `learner_goal` và cần Luna đối thoại

| # | Lớp | `learner_goal` của lượt hiện tại | Ý nghĩa riêng của lời học sinh | Học sinh nói |
| ---: | --- | --- | --- | --- |
| 40 | 3 | Chào Luna bằng tiếng Anh. | Chào đúng rồi hỏi cô đã sẵn sàng chưa. | “Hi, Luna! Are you ready?” |
| 41 | 3 | Giới thiệu tên mình bằng tiếng Anh. | Nói tên rồi hỏi tên Luna. | “I'm Bảo. What's your name?” |
| 42 | 3 | Nói cảm xúc của mình bằng tiếng Anh. | Cho biết mình buồn rồi muốn được động viên. | “I'm sad today. Can you cheer me up?” |
| 43 | 3 | Nói lời cảm ơn bằng tiếng Anh. | Cảm ơn rồi hỏi có thể luyện lại từ vừa học không. | “Thank you! Can we practise that word again?” |
| 44 | 3 | Nói lời tạm biệt bằng tiếng Anh. | Tạm biệt rồi hỏi ngày mai có gặp lại cô không. | “Goodbye, Luna! Will we meet tomorrow?” |
| 45 | 3 | **Đặt câu hỏi cho Luna** về cảm xúc hiện tại của cô. | Thực hiện mục tiêu bằng câu hỏi Luna cần trả lời. | “How are you, Luna?” |
| 46 | 3 | Hỏi Luna cô sống ở đâu bằng tiếng Anh. | Thực hiện mục tiêu hỏi về nơi ở, cần Luna đáp thông tin đã chốt. | “Where do you live, Luna?” |
| 47 | 3 | Nói `Nice to meet you` với Luna. | Bày tỏ vui được gặp rồi hỏi cô có vui không. | “Nice to meet you, Luna. Are you happy to meet me?” |

## `UNCLEAR_INPUT` — transcript được báo `uncertain`

| # | Lớp | `learner_goal` của lượt hiện tại | Phần thông tin chưa xác định | Transcript học sinh (`uncertain`) |
| ---: | --- | --- | --- | --- |
| 48 | 3 | Giới thiệu tên bằng `I'm [tên]`. | Âm thanh bị ngắt trước tên, chưa biết học sinh định nói tên gì. | “I'm...” |
| 49 | 3 | Trả lời `How are you?` bằng cảm xúc tiếng Anh. | Từ chỉ cảm xúc bị cắt, không xác định câu trả lời. | “I'm ha...” |
| 50 | 3 | Hẹn gặp lại ngày mai bằng `See you tomorrow`. | Âm thanh sau `See you` không đủ tin cậy để phân biệt thời điểm. | “See you...” |

## Cách đọc bộ 50 tình huống

- 50 hàng là **50 tình huống hoặc ranh giới ý nghĩa khác nhau trong phạm vi lớp 3**; không dùng hai bản dịch hoặc hai cách chào cùng nghĩa để tăng số lượng.
- Mục tiêu trong bảng là mẫu để phân loại, chưa khẳng định từng lượt này đã tồn tại nguyên dạng trong học liệu hiện tại. Khi kiểm thử, cần ghép câu với `learner_goal` thực tế và `say` đã phát.
- Một lỗi ngữ pháp ở transcript `final` có thể là `ATTEMPT_FAILED` nếu `learner_goal` yêu cầu cấu trúc đó; nó không tự động thành `UNCLEAR_INPUT`.
- `OTHER_INTENT` và `PASSED_WITH_REPLY` phân biệt bằng việc **mục tiêu của lượt đã hoàn thành hay chưa**, không bằng tên gọi riêng của từng câu hỏi/yêu cầu.
- Với hàng 45–46, **hỏi Luna chính là `learner_goal`** nên Teacher đáp rồi hệ thống chuyển lượt.
- Đây là mã **kỳ vọng** để rà soát/kiểm thử sau này, không khẳng định Jev hiện tại đã phân loại đúng.
