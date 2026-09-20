import { expect, test, type Page } from '@playwright/test';

test.beforeEach(async ({ request }) => {
  const apiUrl = process.env.E2E_API_URL ?? `http://localhost:${process.env.E2E_API_PORT ?? '8091'}`;
  await request.post(`${apiUrl}/api/sessions`, {
    data: { unit_id: 'grade05.unit01' },
  });
});

async function openUnit1(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: /Unit 1.*All about me!/i }).click();
}

test('starts at warm-up, recasts naturally, and resets after reload', async ({ page }) => {
  await openUnit1(page);
  await expect(page.getByText("Hello, Quang! I'm Luna.")).toBeVisible();
  await page.getByLabel('Your answer').fill('I live countryside.');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText('I live in the countryside. What do you like about it?')).toBeVisible();
  await expect(page.getByText(/repeat after me/i)).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Choose a unit' })).toBeVisible();
});

test('new session starts clean without session history', async ({ page }) => {
  await openUnit1(page);
  await page.getByRole('button', { name: 'New session' }).click();
  await expect(page.getByText('Session history')).toHaveCount(0);
  await expect(page.getByText(/abandoned/)).toHaveCount(0);
  await expect(page.getByText('Version').locator('..')).toContainText('0');
});

test('keeps the lesson header, composer, and sidebar panels visible on desktop', async ({ page, request }) => {
  const apiUrl = process.env.E2E_API_URL ?? `http://localhost:${process.env.E2E_API_PORT ?? '8091'}`;
  for (let index = 0; index < 5; index += 1) {
    await request.post(`${apiUrl}/api/sessions`, {
      data: { unit_id: 'grade05.unit01' },
    });
  }
  await page.setViewportSize({ width: 1280, height: 720 });
  await openUnit1(page);
  await expect(page.getByRole('heading', { name: 'Practice with Luna' })).toBeVisible();

  const layout = await page.evaluate(() => {
    const composer = document.querySelector<HTMLElement>('.composer');
    const chat = document.querySelector<HTMLElement>('.chat-scroll');
    const inspector = document.querySelector<HTMLElement>('.inspector');
    if (!composer || !chat || !inspector) throw new Error('Lesson layout was not rendered');
    return {
      documentHeight: document.documentElement.scrollHeight,
      viewportHeight: window.innerHeight,
      composerBottom: composer.getBoundingClientRect().bottom,
      chatOverflowY: getComputedStyle(chat).overflowY,
      inspectorClientHeight: inspector.clientHeight,
      inspectorScrollHeight: inspector.scrollHeight,
    };
  });

  expect(layout.documentHeight).toBeLessThanOrEqual(layout.viewportHeight);
  expect(layout.composerBottom).toBeLessThanOrEqual(layout.viewportHeight);
  expect(layout.chatOverflowY).toBe('auto');
  expect(layout.inspectorClientHeight).toBeGreaterThanOrEqual(layout.inspectorScrollHeight);
});
