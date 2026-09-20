import { readFile } from 'node:fs/promises';
import path from 'node:path';

import type { Metadata } from 'next';

import { DesignRulesPage } from '@/components/DesignRulesPage';
import { parseRuleMarkdown } from '@/lib/design-rules';

export const metadata: Metadata = {
  title: 'Nguyên tắc thiết kế Luna',
  description: 'Các nguyên tắc sư phạm và hội thoại của Luna English Tutor.',
};

export default async function DesignPage() {
  const sourcePath = path.resolve(process.cwd(), '../tmp/rule.md');
  const markdown = await readFile(sourcePath, 'utf8');
  return <DesignRulesPage document={parseRuleMarkdown(markdown)} />;
}
