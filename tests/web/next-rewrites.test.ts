import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('local Next.js API proxy', () => {
  beforeEach(() => {
    vi.stubEnv('VPS_HOST', '');
    vi.stubEnv('BACKEND_PORT', '');
    vi.resetModules();
  });

  afterEach(() => vi.unstubAllEnvs());

  it('forwards browser API calls to the local backend by default', async () => {
    const { default: config } = await import('../../web/next.config');
    const rewrites = await config.rewrites?.();

    expect(rewrites).toContainEqual({
      source: '/api/:path*',
      destination: 'http://127.0.0.1:8000/api/:path*',
    });
  });

  it('preserves explicit deployment proxy settings', async () => {
    vi.stubEnv('VPS_HOST', 'https://api.example.test');
    vi.stubEnv('BACKEND_PORT', '8090');
    vi.resetModules();
    const { default: config } = await import('../../web/next.config');
    const rewrites = await config.rewrites?.();

    expect(rewrites).toContainEqual({
      source: '/api/:path*',
      destination: 'https://api.example.test:8090/api/:path*',
    });
  });
});
