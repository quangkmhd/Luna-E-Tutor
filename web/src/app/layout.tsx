import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'Luna English Tutor', description: 'Grade 5 English conversation practice for Quang' };

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
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: localhostHydrationGuard }} />
      </head>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
