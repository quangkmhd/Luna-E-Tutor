import { defineConfig } from 'vitest/config';
import path from 'node:path';

export default defineConfig({
  test: {
    environment: 'jsdom', setupFiles: ['../tests/web/setup.ts'],
    include: ['../tests/web/**/*.test.{ts,tsx}'],
  },
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
});
