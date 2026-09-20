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

test('provider failure is retryable and does not advance state', async ({ page }) => {
  await openUnit1(page);
  await page.getByLabel('Your answer').fill('fixture: provider failure');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.locator('.error-banner')).toContainText('Please try again');
  await expect(page.getByText('Version').locator('..')).toContainText('0');
  await page.getByLabel('Your answer').fill('Hello again');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText('Thank you, Quang. Tell me a little more?')).toBeVisible();
  await expect(page.getByText('Version').locator('..')).toContainText('1');
});

test('Free Talk ends only through the explicit button and shows a summary', async ({ page }) => {
  await openUnit1(page);
  await page.getByLabel('Your answer').fill('fixture: go to free talk');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByRole('button', { name: 'End Free Talk' })).toBeVisible();
  await page.getByRole('button', { name: 'End Free Talk' }).click();
  await expect(page.getByText('What Quang showed today')).toBeVisible();
  await expect(page.getByRole('button', { name: 'End Free Talk' })).toHaveCount(0);
});
