import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DesignRulesPage } from '@/components/DesignRulesPage';
import { parseRuleMarkdown } from '@/lib/design-rules';

describe('design rules page', () => {
  it('turns non-empty Markdown table rows into readable design rules', () => {
    const markdown = `**Các quy tắc tôi sẽ đưa vào thiết kế**

| Nhóm | Cách áp dụng |
| --- | --- |
| Chào | Warm-up chỉ chào và kiểm tra tâm trạng |
| | |
| Free Talk | Chỉ mở sau ba level |
`;

    expect(parseRuleMarkdown(markdown)).toEqual({
      title: 'Các quy tắc tôi sẽ đưa vào thiết kế',
      rules: [
        { group: 'Chào', application: 'Warm-up chỉ chào và kiểm tra tâm trạng' },
        { group: 'Free Talk', application: 'Chỉ mở sau ba level' },
      ],
    });
  });

  it('presents the rules as an executive-readable document', () => {
    render(<DesignRulesPage document={{
      title: 'Các quy tắc tôi sẽ đưa vào thiết kế',
      rules: [
        { group: 'Dạy từ', application: 'Đọc mẫu hai lần trước khi mời trẻ nói.' },
        { group: 'Free Talk', application: 'Chỉ mở sau ba level.' },
      ],
    }} />);

    expect(screen.getByRole('heading', { name: 'Nguyên tắc thiết kế Luna' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Dạy từ' })).toBeVisible();
    expect(screen.getByText('Đọc mẫu hai lần trước khi mời trẻ nói.')).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Free Talk' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'Mở ứng dụng Luna' })).toHaveAttribute('href', '/');
  });

  it('shows the complete teaching system derived from the Unit 1 scenarios', () => {
    render(<DesignRulesPage document={{
      title: 'Các quy tắc tôi sẽ đưa vào thiết kế',
      rules: [
        { group: 'Dạy từ', application: 'Đọc mẫu hai lần trước khi mời trẻ nói.' },
      ],
    }} />);

    expect(screen.getByRole('heading', { name: 'Mục tiêu trải nghiệm' })).toBeVisible();
    expect(screen.getByText(/Học sinh nói tối thiểu 60% toàn buổi/i)).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Vòng lặp dạy học' })).toBeVisible();
    expect(screen.getByText(/Làm mẫu → hỗ trợ → tự diễn đạt → hỏi ngược/i)).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Bộ điều khiển thích ứng' })).toBeVisible();
    expect(screen.getByText(/Phân biệt sai nghĩa, sai ngữ pháp/i)).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Bằng chứng tiến bộ' })).toBeVisible();
    expect(screen.getByText(/độc lập, có hỗ trợ hoặc chưa dùng/i)).toBeVisible();
    expect(screen.getByRole('heading', { name: 'An toàn và hoàn tất' })).toBeVisible();
    expect(screen.getByText(/Không thu thập số điện thoại thật/i)).toBeVisible();
    expect(screen.getByText('docs/UNIT1_ALL_ABOUT_ME_DIALOGUE.md')).toBeVisible();
  });
});
