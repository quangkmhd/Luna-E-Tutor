import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import RootLayout from '@/app/layout';


describe('localhost hydration guard', () => {
  it('removes attributes injected by the browser security extension', async () => {
    const markup = renderToStaticMarkup(<RootLayout><main>Ready</main></RootLayout>);
    const script = markup.match(/<script[^>]*>([\s\S]*?)<\/script>/)?.[1];
    expect(script, 'root layout must install the pre-hydration guard').toBeDefined();

    document.body.setAttribute('bis_register', 'encoded-extension-state');
    document.body.setAttribute('__processed_fbf79ca1-24b2-4486-8687-fd81822cceb7__', 'true');
    document.body.innerHTML = '<div id="existing" bis_skin_checked="1"></div>';

    Function(script!)();

    expect(document.body.hasAttribute('bis_register')).toBe(false);
    expect(document.body.hasAttribute('__processed_fbf79ca1-24b2-4486-8687-fd81822cceb7__')).toBe(false);
    expect(document.querySelector('#existing')?.hasAttribute('bis_skin_checked')).toBe(false);

    const injected = document.createElement('div');
    injected.setAttribute('bis_skin_checked', '1');
    document.body.append(injected);
    await Promise.resolve();

    expect(injected.hasAttribute('bis_skin_checked')).toBe(false);
  });
});
