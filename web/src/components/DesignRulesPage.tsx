import Link from 'next/link';

import type { DesignRuleDocument } from '@/lib/design-rules';

const FEATURED_GROUPS = new Set(['Kịch bản', 'Đánh giá', 'Sửa lỗi', 'Voice']);

const SYSTEM_SECTIONS = [
  {
    number: '01',
    label: 'North star',
    title: 'Mục tiêu trải nghiệm',
    summary: 'Để trẻ là nhân vật chính và luôn có cảm giác mình đang tiến bộ.',
    principles: [
      'Mỗi mục practice có một learner_goal rõ ràng để đối chiếu với lời học sinh.',
      'Luna đọc nguyên văn lời say trong kịch bản.',
      'Mục narration tự chuyển; mục end kết thúc bài sau lời nói cuối.',
    ],
  },
  {
    number: '02',
    label: 'Teaching loop',
    title: 'Vòng lặp dạy học',
    summary: 'Một nhịp dạy dễ dự đoán nhưng vẫn tạo ra hội thoại tự nhiên.',
    principles: [
      'Jev so lời học sinh với learner_goal và trả một mã cho cả lượt.',
      'PASSED chuyển kịch bản; các ngoại lệ đưa qua Teacher.',
      'Teacher hồi đáp đúng ý học sinh trước khi dẫn về mục tiêu nếu em có ý định khác.',
      'Luna không đoán lỗi phát âm chỉ từ transcript chữ.',
    ],
  },
  {
    number: '03',
    label: 'Adaptive control',
    title: 'Bộ điều khiển thích ứng',
    summary: 'Cùng một mục tiêu, nhưng đường đi thay đổi theo trạng thái thật của trẻ.',
    principles: [
      'Lần sai thứ nhất sửa một điểm quan trọng rồi mời thử lại.',
      'Lần sai thứ hai giảm độ khó; lần ba hỗ trợ rõ hơn.',
      'Lần sai thứ tư nói cách đúng rồi phát lời kịch bản kế tiếp.',
      'OTHER_INTENT và UNCLEAR_INPUT không tăng bộ đếm lần sai.',
    ],
  },
  {
    number: '04',
    label: 'Learning evidence',
    title: 'Bằng chứng tiến bộ',
    summary: 'Tiến trình dựa trên điều trẻ đã thực sự nói, không dựa trên phỏng đoán.',
    principles: [
      'Giữ lịch sử lời Luna đã phát và câu học sinh đã nói trong phiên hiện tại.',
      'Một turn_id chỉ được tính một lần, kể cả khi gửi lại.',
      'Bộ đếm gắn với mục practice hiện tại và về không ở mục mới.',
      'Thoát phiên là xóa trạng thái học và lịch sử của phiên.',
    ],
  },
  {
    number: '05',
    label: 'Trust & closure',
    title: 'An toàn và hoàn tất',
    summary: 'Bảo vệ trẻ, đóng vai minh bạch và kết thúc bằng cảm giác hoàn thành.',
    principles: [
      'Học sinh ấn mic để nói và ấn Gửi để yêu cầu chốt transcript.',
      'Không mở quyền bật mic khi Luna đang xử lý hoặc đang nói.',
      'Khi Luna nói xong, mic vẫn tắt cho đến khi học sinh tự bật lại.',
      'Bài Text dùng cùng luồng xử lý và hiển thị lời đáp không qua TTS.',
    ],
  },
] as const;

export function DesignRulesPage({ document }: { document: DesignRuleDocument }) {
  return <main className="design-document">
    <header className="design-hero">
      <nav className="design-nav" aria-label="Điều hướng tài liệu">
        <div className="design-brand"><span>L</span><strong>Luna</strong></div>
        <Link href="/">Mở ứng dụng Luna</Link>
      </nav>
      <div className="design-hero-copy">
        <span className="design-overline">Product design brief · Grade 3 English</span>
        <h1>Nguyên tắc thiết kế Luna</h1>
        <p>{document.title}. Luna đọc kịch bản nguyên văn và hỗ trợ học sinh theo mục tiêu của từng lượt.</p>
        <div className="design-meta">
          <span><strong>{document.rules.length}</strong> nguyên tắc cốt lõi</span>
          <span><strong>3</strong> loại mục kịch bản</span>
          <span><strong>5</strong> mã đánh giá lượt</span>
        </div>
      </div>
    </header>

    <section className="design-rules" aria-labelledby="rules-heading">
      <header className="design-section-heading">
        <span>Teaching system</span>
        <h2 id="rules-heading">Cách Luna vận hành</h2>
        <p>Mỗi nguyên tắc được áp dụng nhất quán trong toàn bộ Unit và mọi lượt hội thoại.</p>
      </header>
      <div className="design-rule-grid">
        {document.rules.map((rule, index) => <article
          className={`design-rule${FEATURED_GROUPS.has(rule.group) ? ' featured' : ''}`}
          key={rule.group}
        >
          <span className="design-rule-number">{String(index + 1).padStart(2, '0')}</span>
          <div>
            <h3>{rule.group}</h3>
            <p>{rule.application}</p>
          </div>
        </article>)}
      </div>
    </section>

    <section className="design-system" aria-labelledby="system-heading">
      <header className="design-section-heading">
        <span>From scenarios to product</span>
        <h2 id="system-heading">Hệ thống dạy học hoàn chỉnh</h2>
        <p>Các cơ chế áp dụng cho bài học theo kịch bản lớp 3.</p>
      </header>
      <div className="design-system-list">
        {SYSTEM_SECTIONS.map((section) => <article className="design-system-section" key={section.number}>
          <header>
            <span className="design-system-number">{section.number}</span>
            <div>
              <span className="design-system-label">{section.label}</span>
              <h3>{section.title}</h3>
              <p>{section.summary}</p>
            </div>
          </header>
          <ul>
            {section.principles.map((principle) => <li key={principle}>{principle}</li>)}
          </ul>
        </article>)}
      </div>
    </section>

    <footer className="design-footer">
      <div><span className="logo-mark">L</span><strong>Luna English Tutor</strong></div>
      <p>Nguồn: <code>docs/grade3_lesson_refactor_spec.md</code></p>
    </footer>
  </main>;
}
