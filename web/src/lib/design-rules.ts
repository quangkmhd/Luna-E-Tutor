export type DesignRule = {
  group: string;
  application: string;
};

export type DesignRuleDocument = {
  title: string;
  rules: DesignRule[];
};

function cleanCell(value: string) {
  return value.trim().replaceAll(' ', ' ');
}

export function parseRuleMarkdown(markdown: string): DesignRuleDocument {
  const title = markdown.match(/^\*\*(.+)\*\*$/m)?.[1].trim()
    ?? 'Các quy tắc thiết kế';
  const rules = markdown.split('\n').flatMap((line) => {
    if (!line.trim().startsWith('|')) return [];
    const cells = line.split('|').slice(1, -1).map(cleanCell);
    if (cells.length < 2) return [];
    const [group, application] = cells;
    if (!group || !application || group === 'Nhóm' || /^-+$/.test(group)) return [];
    return [{ group, application }];
  });

  return { title, rules };
}
