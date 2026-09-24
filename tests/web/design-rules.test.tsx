import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DesignRulesPage } from '@/components/DesignRulesPage';
import { parseRuleMarkdown } from '@/lib/design-rules';

describe('design rules page', () => {
  it('turns non-empty Markdown table rows into readable design rules', () => {
    const markdown = `**Quy tắc dạy học lớp 3**

| Nhóm | Cách áp dụng |
| --- | --- |
| Kịch bản | Luna đọc nguyên văn say |
| | |
| Voice | Học sinh ấn Gửi để chốt transcript |
`;

    expect(parseRuleMarkdown(markdown)).toEqual({
      title: 'Quy tắc dạy học lớp 3',
      rules: [
        { group: 'Kịch bản', application: 'Luna đọc nguyên văn say' },
        { group: 'Voice', application: 'Học sinh ấn Gửi để chốt transcript' },
      ],
    });
  });

  it('presents the rules as an executive-readable document', () => {
    render(<DesignRulesPage document={{
      title: 'Quy tắc dạy học lớp 3',
      rules: [
        { group: 'Kịch bản', application: 'Luna đọc nguyên văn say.' },
        { group: 'Voice', application: 'Học sinh ấn Gửi.' },
      ],
    }} />);

    expect(screen.getByRole('heading', { name: 'Nguyên tắc thiết kế Luna' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Kịch bản' })).toBeVisible();
    expect(screen.getByText('Luna đọc nguyên văn say.')).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Voice' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'Mở ứng dụng Luna' })).toHaveAttribute('href', '/');
  });

  it('shows the complete teaching system derived from the Unit 1 scenarios', () => {
    render(<DesignRulesPage document={{
      title: 'Quy tắc dạy học lớp 3',
      rules: [
        { group: 'Kịch bản', application: 'Luna đọc nguyên văn say.' },
      ],
    }} />);

    expect(screen.getByRole('heading', { name: 'Mục tiêu trải nghiệm' })).toBeVisible();
    expect(screen.getByText(/Mỗi mục practice có một learner_goal/i)).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Vòng lặp dạy học' })).toBeVisible();
    expect(screen.getByText(/Jev so lời học sinh với learner_goal/i)).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Bộ điều khiển thích ứng' })).toBeVisible();
    expect(screen.getByText(/Lần sai thứ nhất sửa một điểm/i)).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Bằng chứng tiến bộ' })).toBeVisible();
    expect(screen.getByText(/Một turn_id chỉ được tính một lần/i)).toBeVisible();
    expect(screen.getByRole('heading', { name: 'An toàn và hoàn tất' })).toBeVisible();
    expect(screen.getByText(/Học sinh ấn mic để nói/i)).toBeVisible();
    expect(screen.getByText('docs/grade3_lesson_refactor_spec.md')).toBeVisible();
  });
});
