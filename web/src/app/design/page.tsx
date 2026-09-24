import type { Metadata } from 'next';

import { DesignRulesPage } from '@/components/DesignRulesPage';
import { parseRuleMarkdown } from '@/lib/design-rules';

export const metadata: Metadata = {
  title: 'Nguyên tắc thiết kế Luna',
  description: 'Các nguyên tắc sư phạm và hội thoại của Luna English Tutor.',
};

const RULE_MARKDOWN = `**Quy tắc dạy học theo kịch bản lớp 3**

| Nhóm                        | Cách áp dụng                                                                                                                     |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Kịch bản | Luna đọc nguyên văn say; narration tự chuyển, practice chờ học sinh, end kết thúc bài. |
| Mục tiêu | Mỗi practice có một learner_goal để Jev đối chiếu với lời học sinh. |
| Đánh giá | Jev chọn đúng một trong năm mã PASSED, ATTEMPT_FAILED, OTHER_INTENT, PASSED_WITH_REPLY, UNCLEAR_INPUT. |
| Sửa lỗi | Sai lần 1 gợi ý sửa; lần 2 giảm độ khó; lần 3 hỗ trợ rõ hơn; lần 4 nói cách đúng rồi chuyển bài. |
| Đối thoại | Teacher hồi đáp ngoại lệ theo một rule cho lượt hiện tại; code quyết định chuyển kịch bản. |
| Voice | Học sinh chủ động bật mic và ấn Gửi; Luna nói xong mic vẫn tắt cho đến khi học sinh ấn lại. |
| Text | Dùng cùng logic bài học và đánh giá như Voice, hiển thị chữ mà không chạy TTS. |
`;

export default function DesignPage() {
  return <DesignRulesPage document={parseRuleMarkdown(RULE_MARKDOWN)} />;
}
