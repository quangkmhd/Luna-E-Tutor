import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const repositoryRoot = resolve(import.meta.dirname, '../..');

describe('global typography', () => {
  it('loads Roboto globally and does not retain legacy font overrides', () => {
    const layout = readFileSync(resolve(repositoryRoot, 'web/src/app/layout.tsx'), 'utf8');
    const globalCss = readFileSync(resolve(repositoryRoot, 'web/src/app/globals.css'), 'utf8');
    const landingCss = readFileSync(resolve(repositoryRoot, 'web/src/app/page.module.css'), 'utf8');
    const talkCss = readFileSync(resolve(repositoryRoot, 'web/src/components/talk/talk.module.css'), 'utf8');
    const styles = [globalCss, landingCss, talkCss].join('\n');

    expect(layout).toContain("import { Roboto } from 'next/font/google'");
    expect(layout).toContain('roboto.className');
    expect(styles).toContain('body,body *{font-family:var(--font-roboto),sans-serif!important}');
  });
});
