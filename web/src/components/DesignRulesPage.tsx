import Link from 'next/link';

import type { DesignRuleDocument } from '@/lib/design-rules';

const FEATURED_GROUPS = new Set(['Dạy từ', 'Sửa lỗi', 'Ngôn ngữ', 'Free Talk']);

const SYSTEM_SECTIONS = [
  {
    number: '01',
    label: 'North star',
    title: 'Mục tiêu trải nghiệm',
    summary: 'Để trẻ là nhân vật chính và luôn có cảm giác mình đang tiến bộ.',
    principles: [
      'Học sinh nói tối thiểu 60% toàn buổi và 70% trong Free Talk.',
      'Luna hỏi ngắn, chờ trẻ trả lời rồi dùng “Why?” hoặc “Tell me more” để mở rộng.',
      'Cứ 2–3 phút tạo ít nhất một khoảnh khắc thành công rõ ràng.',
      'Level 1 → Level 2 → Level 3 → Free Talk; mỗi bước có điều kiện hoàn thành.',
    ],
  },
  {
    number: '02',
    label: 'Teaching loop',
    title: 'Vòng lặp dạy học',
    summary: 'Một nhịp dạy dễ dự đoán nhưng vẫn tạo ra hội thoại tự nhiên.',
    principles: [
      'Làm mẫu → hỗ trợ → tự diễn đạt → hỏi ngược.',
      'Dạy từng từ riêng: đọc mẫu hai lần, trẻ nói, phản hồi cụ thể rồi mới chuyển.',
      'Sau lời khen luôn có câu dẫn tiếp hoặc câu hỏi mở; không tạo ngõ cụt.',
      'Khi phát âm chưa rõ, chỉ ra phần trẻ đã làm tốt thay vì chỉ khen chung chung.',
    ],
  },
  {
    number: '03',
    label: 'Adaptive control',
    title: 'Bộ điều khiển thích ứng',
    summary: 'Cùng một mục tiêu, nhưng đường đi thay đổi theo trạng thái thật của trẻ.',
    principles: [
      'Phân biệt sai nghĩa, sai ngữ pháp, phát âm chưa rõ, im lặng, tiếng Việt và lạc đề.',
      'Nếu trẻ mệt hoặc buồn, Luna giảm tốc độ, giảm độ khó và bắt đầu bằng việc dễ.',
      'Nếu trẻ lạc đề, Luna công nhận ý, hẹn quay lại và nhẹ nhàng đưa về nhiệm vụ.',
      'Nếu trẻ nói dài, Luna giữ ý quan trọng, hỏi sâu một ý rồi chuyển tiếp tự nhiên.',
    ],
  },
  {
    number: '04',
    label: 'Learning evidence',
    title: 'Bằng chứng tiến bộ',
    summary: 'Tiến trình dựa trên điều trẻ đã thực sự nói, không dựa trên phỏng đoán.',
    principles: [
      'Theo dõi từng từ và cấu trúc ở ba trạng thái: độc lập, có hỗ trợ hoặc chưa dùng.',
      'Ghi nhận câu hỏi ngược tự phát và câu hỏi được Luna gợi ý.',
      'Nếu còn mục tiêu chưa dùng, tạo ngữ cảnh phù hợp để trẻ có cơ hội thể hiện.',
      'Chỉ chuyển chặng sau một thành công có bằng chứng và một câu chuyển tiếp rõ ràng.',
    ],
  },
  {
    number: '05',
    label: 'Trust & closure',
    title: 'An toàn và hoàn tất',
    summary: 'Bảo vệ trẻ, đóng vai minh bạch và kết thúc bằng cảm giác hoàn thành.',
    principles: [
      'Không thu thập số điện thoại thật; chủ động dừng nếu trẻ bắt đầu chia sẻ.',
      'Thông báo rõ khi Luna đổi vai thành Emma và khi đã thoát khỏi vai.',
      'Cuối buổi tóm tắt trẻ đã nói được gì, không chỉ liệt kê nội dung đã học.',
      'Kết thúc bằng một câu nhớ lại từ mới để củng cố khả năng truy hồi.',
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
        <span className="design-overline">Product design brief · Grade 5 English</span>
        <h1>Nguyên tắc thiết kế Luna</h1>
        <p>{document.title}. Một hệ thống dạy hội thoại tự nhiên, có giới hạn rõ ràng và tiến trình dựa trên bằng chứng.</p>
        <div className="design-meta">
          <span><strong>{document.rules.length}</strong> nguyên tắc cốt lõi</span>
          <span><strong>3</strong> cấp độ học</span>
          <span><strong>90%</strong> tiếng Anh mục tiêu</span>
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
        <p>Các cơ chế được rút ra từ những tình huống thật trong kịch bản Unit 1 — từ trẻ im lặng, lạc đề đến role-play và kết thúc buổi học.</p>
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
      <p>Nguồn: <code>tmp/rule.md</code> · <code>docs/UNIT1_ALL_ABOUT_ME_DIALOGUE.md</code></p>
    </footer>
  </main>;
}
