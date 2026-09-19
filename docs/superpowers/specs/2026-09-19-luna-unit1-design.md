# Thiết kế Luna — Unit 1 lớp 5

Ngày: 2026-09-19. Trạng thái: bản thiết kế để người dùng duyệt; chưa phải phê duyệt triển khai.

## 1. Mục tiêu và phạm vi

Xây dựng gia sư tiếng Anh bằng giọng nói cho học sinh lớp 1–5. Phiên bản đầu thực hiện Unit 1 lớp 5, All about me!, với lời thoại linh hoạt nhưng tuân thủ quy tắc sư phạm và xử lý các tình huống trong tài liệu nguồn. Kiến trúc cho phép nhập học liệu để tạo unit mới; không coi nội dung tự sinh là đã đạt chất lượng trước kiểm thử.

Nguồn:
- `docs/SPEC_LOP5_UNIT1_LESSON1.md`: quy tắc dạy học.
- `docs/UNIT1_ALL_ABOUT_ME_DIALOGUE.md`: luồng chính và các nhánh hành vi.
- `docs/Global_Success_Khung_Nghe_Noi_3_Level_v3.xlsx`: học liệu lớp/unit/lesson.
- Các quyết định trực tiếp của người dùng trong cuộc thảo luận này được ưu tiên khi nguồn mâu thuẫn.

Người dùng đã chọn: luồng có trạng thái + AI phản hồi linh hoạt; Soniox STT/TTS, Pipecat điều phối, Gemini làm LLM; warm-up chỉ chào; sửa lỗi không bắt nhắc lại. Mục chưa vững được ôn tự nhiên trong Free Talk. Free Talk được phép kết thúc với mục chưa vững và lưu chúng cho buổi sau.

Quyết định model cập nhật: dùng `google/gemini-3.5-flash-lite` qua OpenRouter với `OPENROUTER_API_KEY` cho cả đánh giá bằng chứng và tạo lời cô. Không dùng Jev trong kiến trúc tiếp theo; các thử nghiệm Jev cũ chỉ là lịch sử. Soniox dùng `SONIOX_API_KEY`. Đây là cấu hình được chốt trong spec, chưa phải thông báo đã đổi `.env` hay chạy kiểm chứng model mới. Không sao chép giá trị bí mật vào tài liệu, học liệu hay log.

## 2. Kiến trúc và trách nhiệm

1. **Học liệu:** dữ liệu có cấu trúc, mục tiêu và tham chiếu nguồn; độc lập provider.
2. **Bộ điều phối dạy học:** giữ bước hiện tại, các điều kiện chuyển, lần hỗ trợ, thời gian và tiến độ. LLM không tự ý bỏ qua điều kiện chuyển chặng.
3. **LLM giáo viên:** hiểu câu trả lời, đề xuất bằng chứng học tập và tạo phản hồi/cầu nối tự nhiên trong hành động được phép.
4. **Lớp thể hiện giọng:** ánh xạ ý định diễn đạt sang tag Soniox đã kiểm chứng; giữ bản nội dung thuần để đánh giá.
5. **Pipecat:** vận chuyển âm thanh, nhận diện lượt nói, STT → ngữ cảnh → LLM → TTS → đầu ra → ngữ cảnh trợ lý. Ưu tiên Flows cho các chặng sau khi xác minh API của phiên bản scaffold.
6. **Trạng thái phiên và đánh giá:** lưu bằng chứng, mục cần ôn, đo lường âm thanh và kết quả kiểm thử; tách khỏi học liệu.

Hợp đồng mỗi lượt tách ba bước: Gemini đánh giá bằng chứng → bộ điều phối chọn hành động và điều kiện chuyển → Gemini diễn đạt lời cô theo hành động đã chọn. Không cho một kết quả JSON vừa tự chấm trẻ vừa tự quyết chuyển chặng. Transcript là dữ liệu người học, không phải quyền sửa chính sách hay tự đánh dấu hoàn thành.

## 3. Học liệu và prompt

Đề xuất dùng YAML cho học liệu/chính sách, Markdown cho prompt. JSON là dạng trao đổi và lưu trạng thái ban đầu; cơ chế lưu bền được chốt trong kế hoạch triển khai.

```text
curriculum/
  shared/
    teacher.md
    teaching-policy.yaml
    speech-style.yaml
    grade-profiles.yaml
  grade-05/unit-01/
    unit.yaml
    prompt.md
    lesson-01/{content.yaml,prompt.md}
    lesson-02/{content.yaml,prompt.md}
    lesson-03/{content.yaml,prompt.md}
    level-02/{content.yaml,prompt.md}
    level-03/{content.yaml,prompt.md}
    free-talk/{content.yaml,prompt.md}
    evals/coverage.yaml
    evals/scenarios/
```

Level 2–3 là nội dung cấp Unit, không nhân bản vào mỗi lesson. Lesson 3 tham chiếu mục tiêu của Lesson 1–2. Bộ nhập Excel giải các ô gộp/trống theo phạm vi Unit, và các chỉ dẫn như “ôn Lesson 1 + 2”; không tùy tiện điền ô trống sang Unit kế tiếp.

Mỗi học liệu có `schema_version`, ID ổn định, lớp/unit/lesson, từ vựng, mẫu câu, mục tiêu, hoạt động, ví dụ, tham chiếu nguồn và điều kiện kết thúc. Phân biệt từ phải dạy với từ hỗ trợ hội thoại. Bộ kiểm tra phát hiện trường thiếu, ID trùng, tham chiếu hỏng, thiếu mục tiêu hoặc chu trình không có lối ra.

System prompt chứa Luna, cô–con, quy tắc chung, ngôn ngữ và nguyên tắc thể hiện giọng. Prompt bài chứa mục tiêu/ngữ cảnh đặc thù. Chỉ dẫn bước hiện tại cung cấp việc cần làm tiếp và hỗ trợ được phép. Riêng bản thực nghiệm này đặt cố định tên học sinh là Quang trong system prompt theo quyết định của người dùng; thông tin Quang chia sẻ trong hội thoại vẫn nằm ở trạng thái phiên, không tự ghi thêm thành dữ kiện lâu dài trong prompt chung.

Quy trình thêm Unit: nhập → chuẩn hóa → sinh hoạt động/prompt → kiểm tra độ phủ → chạy eval → duyệt nội dung. Không cần viết lại logic xử lý im lặng, recast hoặc Free Talk cho mỗi Unit.

## 4. Luồng và trạng thái học tập

Chào → Level 1 Lesson 1 → Lesson 2 → Lesson 3 ôn tập → Level 2 → Level 3 → Free Talk → tổng kết. Bản web thực nghiệm kết thúc Free Talk bằng nút người dùng; sản phẩm giọng nói tương lai mới đánh giá lại yêu cầu 10 phút.

Level 1–2 có hỏi đáp luyện tập, không có phiên Free Talk riêng. Mỗi từ mới: cô đọc hai lần → mời trẻ nói → chờ → phản hồi → bước tiếp. Cô không đọc cả danh sách rồi yêu cầu trẻ lặp cả nhóm.

Độ phủ Unit 1:
- L1 Lesson 1: city, class, countryside; giới thiệu lớp/nơi ở.
- L1 Lesson 2: dolphin, pink, sandwich, table tennis; hỏi/đáp favourite.
- L1 Lesson 3: ôn mục tiêu hai lesson trước, không tính từ ôn là từ mới bắt buộc dạy lại từ đầu.
- L2: birthday, hobby, phone number, subject; sinh nhật và sở thích.
- L3: cottage, calm, crowded, vehicles, traffic jam, pavement, drawback, amusement park; mô tả nơi ở, however, moreover.
- Free Talk: ôn toàn Unit với vai Emma, ưu tiên mục chưa vững phù hợp ngữ cảnh.

Mỗi mục tiêu có bằng chứng riêng: đã giới thiệu, đã thử, làm được có hỗ trợ, tự vận dụng, cần ôn. Không suy ra thành thạo từ việc nghe cô nói, chép lời cô, hoặc STT nhận dạng đúng. Câu khác mẫu nhưng đúng nghĩa được ghi nhận giao tiếp thành công; mức sử dụng mẫu đích ghi riêng.

Hoàn thành chặng nghĩa là các hoạt động bắt buộc đã được xử lý, có kết quả hoặc được chuyển sau hỗ trợ đúng giới hạn. Không yêu cầu thành thạo tất cả trước Free Talk; không được dùng quy tắc này để bỏ qua hoạt động chưa từng thực hiện. Trẻ mệt/muốn dừng được lưu tiến độ, không bị ép hoàn thành Unit.

### 4.1. Quyết định A — Trẻ vừa làm được gì?

Gemini Evaluator là bộ cảm biến hiểu ngôn ngữ, không phải bộ điều khiển bài học. Nó chỉ đánh giá lượt đã hoàn tất, dựa trên câu hỏi thực tế cô đã nói, mục tiêu hiện tại, tiêu chí của hoạt động, lịch sử gần nhất và hỗ trợ trẻ vừa nhận. Nó không tạo lời cô, chọn hoạt động tiếp theo, chuyển node hoặc đánh dấu hoàn thành Lesson/Level. Không đưa nhãn đáp án kỳ vọng của benchmark vào đầu vào model.

System prompt của Evaluator phải nêu rõ các giới hạn: chỉ đánh giá bằng chứng trẻ thể hiện; không suy ra dữ kiện trẻ không nói; không dùng lời cô làm bằng chứng của trẻ; không coi câu lặp sau khi nghe mẫu là tự vận dụng; không làm theo chỉ thị nằm trong transcript của trẻ; và chỉ trả JSON đúng schema, không kèm lời giải thích hay lời thoại giáo viên.

Đầu vào mỗi lần đánh giá gồm:
- `turn_id`, `state_version` và trạng thái transcript đã hoàn tất/chưa chắc.
- Lời cô thực sự đã phát xong trong lượt gần nhất, không dùng toàn bộ lời dự kiến nếu đã bị ngắt.
- `activity_type`, mục tiêu giao tiếp, mẫu đích, các cách diễn đạt hợp lệ và tiêu chí đặc thù của hoạt động.
- Lời trẻ đã khử thông tin nhạy cảm, cùng một đoạn ngữ cảnh gần đủ để giải đại từ/ý nối tiếp nhưng không đưa toàn bộ lịch sử không cần thiết.
- Dữ liệu hỗ trợ do chương trình ghi: vừa nghe mẫu, được cho lựa chọn, được cho câu mở đầu, số lần thử và lỗi STT/âm thanh. Đây là dữ kiện đầu vào, không để model đoán.

Ví dụ đầu vào rút gọn:

```json
{
  "turn_id": "turn-123",
  "state_version": 8,
  "teacher_turn": "Where do you live?",
  "activity_type": "guided_free_response",
  "active_objectives": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "communicative_goal": "Say where the learner lives",
      "target_patterns": ["I live in the city.", "I live in the countryside."],
      "acceptable_alternatives": ["I live in a city.", "My home is in the countryside."]
    }
  ],
  "support_given": {
    "model_spoken_recently": false,
    "choices_given": false,
    "sentence_starter_given": false
  },
  "transcript_status": "final",
  "learner_transcript": "I live countryside."
}
```

Kết quả có schema gồm:
- `turn_id`, `state_version`: gắn kết quả đúng lượt và đúng phiên bản trạng thái.
- `response_kind`: câu trả lời, hỏi nghĩa, hỏi cô, lạc đề, chưa biết, hoặc chưa đủ dữ liệu. Cảm xúc lưu riêng vì có thể cùng xuất hiện với câu trả lời đúng.
- `emotional_signals`: danh sách tín hiệu cảm xúc; không làm mất bằng chứng học tập khác trong cùng lượt.
- `objective_evidence`: danh sách bằng chứng theo từng `objective_id`, vì một lượt có thể đáp ứng nhiều mục tiêu.
- `meaning_status`: `satisfied`, `partially_satisfied`, `wrong_semantic_category`, `not_demonstrated`, hoặc `uncertain`. Đánh giá trẻ có trả lời đúng yêu cầu, không kiểm chứng sự thật về đời sống trẻ.
- `target_form_status`: `correct_target_form`, `valid_alternative`, `error_in_target_form`, `not_used`, hoặc `uncertain`. Mẫu đích là cấu trúc với ô trống, không phải câu phải trùng từng chữ.
- `evidence_quote`: trích nguyên văn có thật từ lời trẻ đã khử thông tin nhạy cảm. Câu của cô không được tính là bằng chứng của trẻ.
- `recast_needed`, `corrected_form`: chỉ sửa lỗi đã thể hiện rõ; không xem câu ngắn tự nhiên, cách diễn đạt khác đúng, hay câu hỏi nghĩa là lỗi cần recast. Không tự bịa ý định để tạo câu sửa.
- `needs_clarification`, `ambiguity_reason`: giới hạn đánh giá. Không dùng xác suất model tự khai như một thước đo đã hiệu chỉnh.

Ví dụ đầu ra cho `I live countryside.`:

```json
{
  "turn_id": "turn-123",
  "state_version": 8,
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "satisfied",
      "target_form_status": "error_in_target_form",
      "evidence_quote": "I live countryside",
      "recast_needed": true,
      "corrected_form": "I live in the countryside."
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

Mức độc lập lấy từ lịch sử hỗ trợ do chương trình ghi nhận: vừa nghe mẫu và nói lại = bắt chước; trả lời sau lựa chọn/gợi ý = có hỗ trợ; tự trả lời không có mẫu gần đó = bằng chứng độc lập. Gemini không được gán độc lập chỉ vì câu đúng. Tiếng Việt đúng nghĩa được ghi nhận giao tiếp thành công, nhưng không phải bằng chứng dùng mẫu tiếng Anh.

Lỗi STT, transcript thiếu hoặc câu còn dang dở không phải lỗi học sinh. Khi không đủ bằng chứng, Evaluator phải trả `uncertain`/`needs_clarification` thay vì bị ép chọn đúng hoặc sai. Trạng thái im lặng do đồng hồ/sự kiện xác định, không suy ra chỉ từ chuỗi rỗng. Dữ liệu nhạy cảm được xử lý trước model; sự kiện privacy không xóa bằng chứng học tập đã có ở những lượt khác.

Prompt có few-shot cho tối thiểu các trường hợp: câu một từ đúng (`Countryside.`), lỗi mẫu nhưng đúng ý (`I live countryside.`), câu đúng mẫu, cách diễn đạt khác hợp lệ, hỏi nghĩa bằng Anh/Việt, trả lời tiếng Việt đúng ý, sai loại nghĩa (`Pink` cho animal), cảm xúc đi cùng câu trả lời, transcript chưa hoàn tất và nhiều mục tiêu trong một lượt. Few-shot phải dùng đúng schema và không chứa quyết định chuyển node hay lời cô.

Độ tin cậy của Evaluator đến từ prompt rõ + structured output nghiêm ngặt + học liệu chuẩn hóa + validation bằng code + nhánh `uncertain` + bộ dữ liệu có nhãn + chạy lặp đo độ ổn định. `temperature=0` không được coi là bảo đảm tất định. Backend kiểm tra `turn_id`, `state_version`, `objective_id`, enum, trích đoạn có thật và tính nhất quán giữa các trường trước khi chấp nhận kết quả.

### 4.2. Quyết định B — Bây giờ nên làm gì tiếp?

Bộ điều phối dùng bằng chứng đã kiểm tra cùng trạng thái: bước đang dạy, hoạt động đã thực hiện, mức hỗ trợ, số lần thử, thời gian từ thành công gần nhất, hàng đợi ôn và yêu cầu dừng. Kết quả tách `feedback_action` (ghi nhận/recast/giải thích/trấn an) khỏi `progression_action` (giữ bước/giảm khó/chuyển mục/chuyển chặng/lưu và dừng). Một lượt có thể vừa recast vừa chuyển tiếp.

Thứ tự xử lý: yêu cầu dừng và privacy → lỗi vận hành/câu chưa rõ → nhu cầu cảm xúc/hỏi nghĩa/hỏi cô → bằng chứng học tập → giới hạn hỗ trợ và điều kiện chuyển. Vẫn giữ bằng chứng trẻ làm được khi trong cùng lượt trẻ biểu lộ cảm xúc. Hỏi nghĩa và lỗi vận hành không tăng bộ đếm trả lời sai.

| Tình huống | Ghi nhận trẻ làm được | Hành động tiếp |
|---|---|---|
| Cô vừa dạy `city`, trẻ nói lại `city` | Đã thử từ với mẫu hỗ trợ; chưa chứng minh tự nhớ hay đúng âm vị | Phản hồi rồi chuyển từ tiếp theo theo hoạt động; để cơ hội vận dụng sau |
| Hỏi nơi ở, trẻ nói `Countryside` | Đúng ý và từ; chưa thể hiện cả mẫu câu | Ghi nhận, có thể lồng mẫu tự nhiên rồi tiếp tục; không bắt nói lại |
| `I live countryside` | Đúng ý, mẫu còn lỗi | Recast rồi tiếp tục, ghi cấu trúc vào hàng đợi ôn |
| `I enjoy playing table tennis` khi đích là `My hobby is ...` | Giao tiếp đúng, diễn đạt khác đúng | Tiếp tục; mẫu đích còn thiếu bằng chứng, không chấm câu này sai |
| Hỏi favourite animal, trẻ đáp `Pink` | Sai loại nghĩa; chưa có bằng chứng mục tiêu | Giải thích ngắn/đưa lựa chọn; không tự bịa con vật trẻ muốn nói để recast |
| `Hobby nghĩa là gì?` | Trẻ đang hỏi nghĩa | Giải thích rồi tạo cơ hội dễ; không recast câu hỏi, không cộng lần thất bại |
| Đã thử hai lần vẫn khó | Đã tham gia nhưng chưa vững | Chuyển mục, đánh dấu cần ôn; không đánh dấu thành thạo |
| Trẻ tự dùng đúng mục đang chờ ôn | Có bằng chứng độc lập trong ngữ cảnh | Cập nhật mục đó; bỏ câu ôn dự kiến nếu không còn cần |

Điều kiện chuyển từ phụ thuộc hoạt động: lượt bắt chước từ cần đã phát mẫu đủ, có cơ hội trả lời và phản hồi, hoặc đã xử lý giới hạn hỗ trợ; bài tự vận dụng dùng tiêu chí giao tiếp/mẫu câu ghi trong học liệu. Hoàn thành một lượt luyện không đồng nghĩa mục tiêu đã vững.

Điều kiện chuyển chặng: mọi hoạt động bắt buộc có trạng thái hoàn tất hoặc chuyển sau hỗ trợ có lý do; kiểm tra lượt hỏi lại cô và các yêu cầu của chặng. Lượt đã hết giới hạn hỗ trợ không được đổi thành một câu hỏi tương đương để ép luyện tiếp. Nếu yêu cầu hỏi cô chưa đạt sau hỗ trợ, ghi là đã tạo cơ hội nhưng chưa đạt, không bịa rằng trẻ đã hỏi. Dừng sớm lưu tiến độ riêng. Free Talk chỉ mở khi các chặng tiên quyết đã được xử lý; không cần mọi mục tiêu đều vững.

Không có ngưỡng thành thạo chung kiểu một câu đúng hoặc điểm 0.8. Lưu các bằng chứng theo mục tiêu và mức hỗ trợ; số cơ hội độc lập cần để kết luận vững phải được hiệu chỉnh bằng thực nghiệm. Trong thời gian chưa hiệu chỉnh, báo “đã có bằng chứng tự dùng” thay vì “đã thành thạo”.

### 4.3. Tạo lời cô và xác thực

Thực nghiệm tiếp theo dùng hai lần gọi cùng model: lần 1 trả bằng chứng theo JSON schema; chương trình quyết định; lần 2 nhận hành động, mục tiêu kế tiếp, ý trẻ và các điều cấm để viết lời cô. Lần 2 không có quyền cập nhật tiến độ. Chi phí/độ trễ hai lần gọi phải đo trước khi tối ưu gộp lượt.

OpenRouter dùng structured output cho đánh giá, nhưng schema đúng không bảo đảm đánh giá đúng. Kiểm tra ID mục tiêu, trích đoạn có thật, enum, tính nhất quán và state version. Response lỗi hoặc quá hạn không tăng mastery, không tăng số lần trẻ sai và không chuyển chặng. Chỉ áp dụng một lần cho mỗi turn ID; bỏ response cũ sau ngắt lời/thay đổi trạng thái. Hoạt động cần cô phát mẫu chỉ được ghi là đã dạy khi âm thanh tương ứng đã phát.

Kiểm thử riêng: (A) độ đúng bằng chứng so với nhãn, (B) luật chuyển trên bằng chứng cố định, (C) lời cô tuân thủ hành động, (D) hội thoại nhiều lượt kết hợp cả ba. Bộ mới phải có ngữ cảnh hỗ trợ, câu tương đương đúng, tiếng Việt, nhiều ý trong một lượt, lỗi STT, hai lần chưa đạt, câu hỏi lại và ôn Free Talk. Điểm benchmark cũ có nhãn chồng lấn và kết quả privacy bị luật cục bộ ghi đè, nên không dùng để kết luận năng lực model mới.

Nguồn cấu hình: https://openrouter.ai/google/gemini-3.5-flash-lite và https://openrouter.ai/docs/guides/features/structured-outputs .

## 5. Quy tắc và cách kiểm tra

| ID | Quy tắc | Bằng chứng/kiểm thử |
|---|---|---|
| R01 | Luna, English Tutor; cô–con nhất quán; phân biệt buổi đầu/buổi sau | Eval cả hai lời chào và cách xưng hô |
| R02 | Warm-up chỉ chào, kiểm tra tâm trạng, dẫn vào bài | Không dạy từ/mini game ở warm-up; đủ 10 nhánh |
| R03 | Từng từ mới đọc mẫu hai lần trước khi mời trẻ nói | Thứ tự sự kiện và audio đầu ra; không đọc gộp |
| R04 | Làm mẫu → hỗ trợ → trẻ tự diễn đạt; trạm luyện theo yêu cầu 4–6 lượt | Theo dõi hoạt động, hỗ trợ và lượt; ngoại lệ dừng sớm có lý do |
| R05 | Trẻ hỏi lại ít nhất một lần mỗi trạm | Ghi nhận cả câu hỏi tự phát và có hỗ trợ; không chỉ đếm lời cô mời |
| R06 | Nghe hết → phản hồi ý → recast → tiếp tục; không bắt lặp sau sửa | Eval ngữ pháp/nghĩa/tiếng Việt; audio kiểm tra không ngắt vì lỗi |
| R07 | Chấp nhận câu ngắn; hỗ trợ từ chưa hiểu và sai loại từ | Eval city/countryside, pink/animal, hobby, drawback, traffic jam |
| R08 | Im lặng khoảng 8 giây sau khi cô nói xong; không khi trẻ đang nói | Đồng hồ sự kiện âm thanh; hủy gợi ý cũ khi trẻ bắt đầu nói |
| R09 | Tối đa hai lần thử ở cùng điểm rồi giảm khó/chuyển | Bộ đếm theo mục tiêu; im lặng hai lần, lỗi lặp, không hỏi lại trá hình |
| R10 | Thành công mỗi 2–3 phút; sau 3 phút không có thì giảm khó | Đồng hồ và bằng chứng thật; không dùng lời khen của cô làm bằng chứng |
| R11 | Lạc đề/kể dài: nghe, ghi nhận, nối về bài; mệt/buồn: hỗ trợ | Nhánh kết hợp cảm xúc + tiếng Việt/lạc đề; không ép trả lời |
| R12 | Anh 90%, Việt 10%; Việt cho khái niệm mới, cảm xúc, khen cuối buổi | Đánh giá ngữ cảnh và số đo ngôn ngữ |
| R13 | Sau khen/phản hồi có câu dẫn hoặc hoạt động tiếp | Không có ngõ cụt giữa bài; lời chào kết thúc được phép kết thúc |
| R14 | phone number chỉ luyện giả định, không hỏi số thật | Nhánh trẻ tự đọc số thật: chuyển khỏi nội dung đó, không nhắc lại/lưu vào hồ sơ học tập |
| R15 | Thông báo vào/ra vai; Luna trở lại cuối buổi | Eval chuyển vai và tổng kết đúng thành tích thực tế |
| R16 | Free Talk sau cả ba level, có ôn từ/cấu trúc còn yếu | Kiểm tra điều kiện mở và cơ hội sử dụng, không chỉ tìm từ trong lời cô |
| R17 | Trẻ nói ≥60% buổi và ≥70% Free Talk | Audio thực tế; warm-up vẫn tính vào toàn buổi |
| R18 | Khen cụ thể có bằng chứng, không bịa nhận xét âm vị | Transcript không đủ để khẳng định nghe đúng /s/ hoặc trọng âm |
| R19 | Cảm xúc/tag/nhấn nhá đúng ngữ cảnh và giọng đã chọn | Kiểm thử âm thanh, không đọc tag, không gây biến dạng từ mẫu |
| R20 | Mục chưa vững được lưu tiếp sau Free Talk | Tiến độ trước/sau, không giả vờ đã thành thạo để đóng buổi |

Quy tắc ưu tiên khi tài liệu mâu thuẫn: quyết định người dùng → quy tắc sư phạm đã thống nhất → mục tiêu học liệu → lời thoại ví dụ. Ví dụ không phải đáp án bắt buộc hoặc dữ kiện về cuộc sống của mọi trẻ.

Các diễn giải cụ thể: dạy từ L2 trước câu hỏi dùng từ đó dù đoạn bổ sung nằm sau trong file; không dùng “then you try” sau sửa lỗi; không kết luận trẻ sống ở thành phố chỉ từ mô tả có nhà cao tầng; không phủ nhận trẻ sống ở nông thôn có nhiều xe. Nhánh số điện thoại là ngoại lệ bảo vệ thông tin, không phải ngắt trẻ để sửa lỗi.

## 6. Free Talk ôn tự nhiên

Hàng đợi ôn lưu mục tiêu, loại khó khăn (nghĩa/nhớ từ/cấu trúc), bằng chứng, mức hỗ trợ, lần gặp gần nhất và thông tin trẻ liên quan. Không lưu chỉ một nhãn “sai”.

Mỗi lượt: hiểu ý trẻ → ghi nhận mục tiêu trẻ tự đáp ứng → tìm mục ôn phù hợp chuyện hiện tại → chọn một hành động → diễn đạt. Ưu tiên phản hồi trực tiếp câu trẻ hỏi trước khi dẫn sang mục ôn. Không có cầu nối phù hợp thì tiếp tục chuyện, để mục đó chờ.

Mức hỗ trợ: cơ hội tự diễn đạt → gợi ý ngữ cảnh → lựa chọn/mẫu lồng trong phản hồi → chuyển tiếp nếu còn khó. Xen điều trẻ làm tốt với điểm yếu. Mỗi thời điểm tập trung một mục; không quay lại ngay bằng câu hỏi tương đương sau khi hết giới hạn hỗ trợ. Trẻ tự dùng đúng mục đang chờ thì cập nhật và bỏ câu ôn dự kiến.

Ví dụ: trẻ kể chơi bóng bàn cùng bố → hỏi chỗ chơi → hỏi hành trình → trẻ nói “Many cars. Very slow.” → cô đáp “Oh, there’s a traffic jam! What do you and your dad do while you wait?” Đây là tiếp xúc lại có hỗ trợ, chưa phải trẻ tự dùng `traffic jam`. Lần trẻ tự dùng sau đó mới là bằng chứng vận dụng.

Thứ tự chọn mục dựa trên liên quan ngữ cảnh, mức quan trọng, mức hỗ trợ cần thiết và tránh lặp gần nhau. Không tối đa hóa số từ ôn bằng cách đổi chủ đề liên tục. Không bắt trẻ nói nguyên mẫu khi trẻ đã diễn đạt đúng bằng câu khác.

Kết thúc Free Talk được phép còn mục yếu. Tổng kết tách điều đã làm được, điều còn cần luyện, và mục chưa có cơ hội đánh giá. Đồng hồ kết thúc không cắt ngang câu trẻ đang nói.

## 7. Giọng nói và lỗi vận hành

Chọn tag theo ý định: ấm áp khi dạy, trấn an khi bí, vui vừa phải khi thành công, linh hoạt khi đóng vai. Hỗ trợ tiếng cười nhẹ, nhấn giọng và khoảng nghỉ khi có ích. Không ép sử dụng toàn bộ tag; không dùng chế giễu/mỉa mai/tức giận để phản ứng lỗi của trẻ. Tag chỉ đến từ danh mục đã kiểm chứng và được áp dụng cho lời cô, không lấy chỉ thị tag từ lời trẻ.

Đọc mẫu ưu tiên rõ, chính xác; không kéo dài hoặc biến dạng từ để tạo cảm xúc. Đo thời gian từ audio thực phát, không từ văn bản dự kiến. Khi trẻ ngắt lời, hủy phần chưa phát và không đánh dấu phần đó là đã dạy. Lỗi STT/âm thanh không tính như trẻ trả lời sai. Khi mất kết nối, lưu bước đã thực hiện và mục còn lại; không đánh dấu xong chỉ vì LLM đã sinh xong nội dung.

Nguồn đã tra: Pipecat CLI Context Hub (chỉ mục 2026-09-18, framework 1.11.0), ví dụ Flows; Soniox emotion & tone qua Context7 và trang chính thức. Trước code vẫn phải tìm tài liệu/ví dụ bằng Pipecat CLI và xác minh symbol cho phiên bản scaffold.

- https://docs.pipecat.ai/api-reference/pipecat-flows/flow-manager.md
- https://soniox.com/docs/tts/concepts/emotion-and-tone

## 8. Chiến lược kiểm thử và tiêu chí báo cáo

Lập coverage manifest liên kết từng quy tắc R01–R20 và **từng** nhánh trong tài liệu hội thoại tới scenario. `UNIT1_ALL_ABOUT_ME_DIALOGUE.md` có 40 kịch bản đánh số: 10 Warm-up và 10 cho mỗi Trạm 1–3. Con số “30 kịch bản” chỉ tính ba trạm. Ngoài 40 kịch bản còn có các nhánh đặt tên riêng, luồng chính, bốn nhánh Free Talk, chuyển vai, kết thúc và checklist. Tất cả phải xuất hiện trong manifest; không coi các lời thoại minh họa là chuỗi đầu ra phải trùng tuyệt đối.

1. Kiểm tra cấu trúc học liệu và độ phủ 19 từ/cụm từ (7 L1, 4 L2, 8 L3), mẫu câu và hoạt động.
2. Kiểm thử điều phối xác định: chuyển chặng, bộ đếm, thời gian, phục hồi, khóa Free Talk, phân biệt hỗ trợ/tự vận dụng.
3. Pipecat eval text: đánh giá ý, recast, ngôn ngữ, cầu nối, hỏi ngược, không ép lặp; dùng LLM judge khi cần đánh giá nghĩa. Biến thể cách diễn đạt và tình huống kết hợp ngoài ví dụ gốc.
4. Pipecat eval audio: Soniox STT/TTS thực, im lặng, turn-taking, ngắt lời, nhấn giọng, tag, phát âm mẫu và thời lượng. Audio tổng hợp giúp kiểm tra pipeline nhưng không thay thế kiểm chứng giọng trẻ thực tế.
5. Chạy toàn buổi, kiểm tra coverage, tỷ lệ nói, thời điểm giảm khó, ôn mềm và lưu mục chưa vững.

Báo cáo mỗi quy tắc: đạt/không đạt/chưa chạy/không áp dụng, bằng chứng và giới hạn. Không gọi toàn bộ hệ thống “đã đạt” khi còn kiểm thử bắt buộc chưa chạy. Quy tắc logic phải có kiểm tra xác định; tính tự nhiên cần đánh giá ngữ nghĩa và nghe mẫu. Không hứa bảo đảm mọi đầu ra LLM hay mọi hành vi của trẻ bằng một lần chạy thành công.

### 8.1. Vòng lặp thực nghiệm trước khi xây toàn bộ ứng dụng

Giai đoạn code đầu tiên là evaluation harness cho ba phần tách biệt, chưa phải giao diện hoặc Pipecat:

1. Chuyển học liệu và toàn bộ kịch bản/nhánh Unit 1 thành scenario có ID ổn định, trạng thái đầu vào, lời trẻ, nhãn bằng chứng mong đợi, hành động được phép/cấm và tiêu chí lời cô.
2. Gọi `google/gemini-3.5-flash-lite` qua OpenRouter với Evaluator prompt và structured output mới; kiểm tra schema, ID, trích đoạn và các quan hệ logic trước khi chấm nội dung.
3. Đưa bằng chứng đã hợp lệ qua Teaching Engine; kiểm thử chuyển bước/node bằng luật xác định, không dùng LLM judge cho các luật cứng.
4. Đưa `TeacherTurnRequest` do Teaching Engine tạo vào Gemini Teacher; kiểm tra điều cấm bằng code và đánh giá ngữ nghĩa/độ tự nhiên riêng.
5. Chạy mỗi case nhiều lần để đo độ đúng, độ ổn định và độ trễ; phân nhóm lỗi theo Evaluator, Teaching Engine hoặc Teacher thay vì chỉ báo một điểm tổng.
6. Sửa đúng thành phần gây lỗi, chạy lại tập phát triển và sau đó chạy tập giữ riêng. Chỉ nhận thay đổi khi cải thiện mục tiêu và không làm hỏng hard rule hoặc gây hồi quy trên holdout.

Không để model tự sửa prompt rồi tự tuyên bố đạt trên chính tập đã dùng để sửa. Chia dữ liệu thành:
- **Development set:** dùng tìm lỗi, bổ sung few-shot và cải thiện prompt/schema.
- **Holdout set:** không đưa vào prompt hoặc vòng sửa; chỉ dùng xác nhận thay đổi tổng quát hóa.
- **Hard-rule suite:** privacy, không bắt nhắc lại sau recast, tối đa hai lần thử, không tính lỗi hệ thống là lỗi trẻ, không tự chuyển node và không giả bằng chứng. Các luật này phải được xác định bằng code và đạt toàn bộ case bắt buộc.
- **Human review set:** mẫu lời Luna cần người nghe đánh giá tự nhiên, phù hợp lứa tuổi và không máy móc. LLM judge chỉ là tín hiệu hỗ trợ, không thay người duyệt.

Mỗi vòng lưu phiên bản prompt, model, scenario set, output thô đã khử dữ liệu nhạy cảm, kết quả validation, metric theo từng trường, latency và danh sách hồi quy. Không chỉnh prompt chỉ để tăng điểm tổng; lỗi privacy/chuyển trạng thái có mức ưu tiên cao hơn lỗi diễn đạt.

### 8.2. Trạng thái bằng chứng hiện tại

Prototype trong `tmp/jev-gemini-spike` chỉ có 18 case tự tạo, schema cũ và thử nghiệm Jev/Gemini trước quyết định kiến trúc hiện tại. Năm unit test tiện ích của prototype kiểm tra redaction, validation và privacy guard; chúng không kiểm tra chất lượng dạy học. Chưa có lần chạy nào bao phủ 40 kịch bản đánh số và các nhánh bổ sung bằng `google/gemini-3.5-flash-lite` qua OpenRouter; chưa có Gemini Teacher, Teaching Engine nhiều lượt, chạy toàn Unit hoặc vòng lặp cải thiện development/holdout. Kết quả cũ không được dùng để tuyên bố kiến trúc mới đã đạt.

## 9. Bản web thực nghiệm đã thống nhất

- Phạm vi: toàn bộ Unit 1 lớp 5, từ chào hỏi qua Level 1 Lesson 1–3, Level 2, Level 3, Free Talk và tổng kết.
- Giao diện dùng Next.js App Router, React và TypeScript. Backend dùng Python/FastAPI; SQLite lưu phiên, lượt hội thoại, bằng chứng và chuyển trạng thái. Đây là lựa chọn đã chốt cho bản thực nghiệm, chưa phải phần đã triển khai.
- Bản đầu chạy local cho một người thử nghiệm, không đăng nhập và không có hồ sơ nhiều học sinh. Frontend và backend là hai tiến trình local; giao tiếp bằng REST JSON. `OPENROUTER_API_KEY` chỉ được đọc ở backend và không bao giờ gửi xuống trình duyệt.
- Backend là nguồn sự thật cho trạng thái bài. Trình duyệt chỉ hiển thị trạng thái server trả về; tải lại trang không tự suy diễn hoặc cập nhật tiến độ.
- Mỗi thao tác gửi lời trẻ có `turn_id` để chống xử lý trùng. Trong lúc chờ, khóa gửi lặp cho lượt đó. API lỗi giữ nguyên bước học và cho phép thử lại; không tính là trẻ sai.
- Phản hồi bản đầu trả trọn gói sau khi hoàn tất hai bước model và quyết định chương trình. Chưa streaming từng token; lựa chọn này giúp đo đúng độ trễ toàn lượt và giữ lời cô nhất quán với trạng thái đã lưu.
- SQLite ghi trạng thái phiên và lượt đã hoàn tất trong một transaction. Lịch sử không chứa khóa API; dữ liệu nhạy cảm được che trước khi gọi model và trước khi ghi log chẩn đoán.
- Chế độ học từ đầu; không có màn chọn nhảy đến tình huống trong bản đầu.
- Học sinh tên Quang được đặt cố định trong system prompt thử nghiệm; không cần nhập tên hay tạo hồ sơ học sinh.
- Lưu lịch sử hội thoại và tiến độ. Nút “Bắt đầu phiên mới” tạo phiên độc lập từ lời chào, giữ nguyên lịch sử phiên cũ.
- Nếu đang có lượt chưa gửi hoặc request đang chạy, nút “Bắt đầu phiên mới” yêu cầu xác nhận rồi đánh dấu phiên hiện tại là `abandoned`; không xóa lịch sử. Phiên mới luôn bắt đầu ở warm-up.
- Free Talk của bản web văn bản không giới hạn thời gian. Người dùng bấm “Kết thúc” để chuyển sang tổng kết, lưu kết quả và các mục chưa vững. Không tự kết thúc theo đồng hồ và không dùng mốc 10 phút làm điều kiện đạt của bản thử nghiệm.
- Quyết định không giới hạn thời gian ở trên ưu tiên hơn các mô tả “Free Talk 10 phút” trong tài liệu này đối với bản web thử nghiệm; chưa thay đổi tiêu chí thời lượng của sản phẩm giọng nói tương lai.
- Bảng quan sát hiển thị bằng chứng trẻ vừa thể hiện, quyết định chương trình và trạng thái bài; đây là thông tin kiểm thử, không phải lời cô đọc cho học sinh.

## 10. Bước tiếp theo

Người dùng yêu cầu bỏ qua phần đề xuất cần duyệt trước triển khai; các đề xuất đó không được coi là quyết định đã phê duyệt hoặc điều kiện phải chốt để tiếp tục. Các quy tắc dạy học đã thống nhất vẫn áp dụng.

Phạm vi hiện tại: spec đã đủ để viết implementation plan. Thứ tự triển khai bắt buộc bắt đầu bằng evaluation harness và vòng lặp ở mục 8.1; chỉ xây toàn bộ trang web quanh phần lõi sau khi có báo cáo development/holdout và danh sách giới hạn còn lại. Prototype cũ trong `tmp/jev-gemini-spike` không chứng minh luồng dạy hay model mới đã đạt. Chưa scaffold bot hoặc triển khai dịch vụ. Khi chuyển sang tích hợp Pipecat mới tra CLI, scaffold với eval và xác minh API theo yêu cầu dự án.
