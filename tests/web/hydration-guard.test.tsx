import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import RootLayout from '@/app/layout';


describe('Windows browser hydration guard', () => {
  it('removes Bitdefender attributes added before and during hydration', async () => {
    vi.useFakeTimers();
    try {
      const markup = renderToStaticMarkup(<RootLayout><main>Ready</main></RootLayout>);
      const script = markup.match(/<script[^>]*>([\s\S]*?)<\/script>/)?.[1];
      expect(script, 'root layout must install the pre-hydration guard').toBeDefined();

      document.body.innerHTML = '<div id="existing" bis_skin_checked="1"></div>';
      Function(script!)();
      expect(document.querySelector('#existing')?.hasAttribute('bis_skin_checked')).toBe(false);

      const injected = document.createElement('div');
      injected.setAttribute('bis_skin_checked', '1');
      document.body.append(injected);
      await Promise.resolve();
      expect(injected.hasAttribute('bis_skin_checked')).toBe(false);
    } finally {
      vi.useRealTimers();
    }
  });
});
