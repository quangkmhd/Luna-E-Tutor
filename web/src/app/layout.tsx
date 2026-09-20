import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'Luna English Tutor', description: 'Unit 1 English conversation experiment for Quang' };

const bitdefenderHydrationGuard = `
(() => {
  if (location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') return;
  const attribute = 'bis_skin_checked';
  const clean = (root) => {
    if (root.nodeType === Node.ELEMENT_NODE && root.hasAttribute(attribute)) {
      root.removeAttribute(attribute);
    }
    root.querySelectorAll?.('[' + attribute + ']').forEach((element) => {
      element.removeAttribute(attribute);
    });
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
    attributeFilter: [attribute],
    childList: true,
    subtree: true,
  });
  setTimeout(() => observer.disconnect(), 5000);
})();`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><head><script dangerouslySetInnerHTML={{__html: bitdefenderHydrationGuard}} /></head><body>{children}</body></html>;
}
