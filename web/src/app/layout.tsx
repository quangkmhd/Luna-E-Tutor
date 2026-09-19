import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'Luna English Tutor', description: 'Unit 1 English conversation experiment for Quang' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
