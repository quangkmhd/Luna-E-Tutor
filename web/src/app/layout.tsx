import type { Metadata } from 'next';
import { Roboto } from 'next/font/google';
import './globals.css';
import './learner.css';

export const metadata: Metadata = { title: 'Luna English Tutor', description: 'English conversation practice with Luna' };

const roboto = Roboto({
  subsets: ['latin', 'vietnamese'],
  weight: ['400', '500', '700', '900'],
  display: 'swap',
  variable: '--font-roboto',
});

const localhostHydrationGuard = `
(() => {
  if (location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') return;

  const injected = (name) =>
    name === 'bis_skin_checked' || name.startsWith('bis_') || name.startsWith('__processed_');

  const cleanElement = (element) => {
    for (const attribute of [...element.attributes]) {
      if (injected(attribute.name)) element.removeAttribute(attribute.name);
    }
  };

  const clean = (root) => {
    if (root.nodeType === Node.ELEMENT_NODE) cleanElement(root);
    root.querySelectorAll?.('*').forEach(cleanElement);
  };

  clean(document);
  const observer = new MutationObserver((records) => {
    for (const record of records) {
      if (record.type === 'attributes') clean(record.target);
      else record.addedNodes.forEach(clean);
    }
  });
  observer.observe(document.documentElement, {
    attributes: true,
    childList: true,
    subtree: true,
  });
  setTimeout(() => observer.disconnect(), 5000);
})();`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${roboto.className} ${roboto.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: localhostHydrationGuard }} />
      </head>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
