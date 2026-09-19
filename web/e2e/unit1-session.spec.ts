import { expect, test } from '@playwright/test';

test.beforeEach(async ({ request }) => {
  await request.post('http://localhost:8091/api/sessions');
});

test('starts at warm-up, recasts naturally, and resumes after reload', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText("Hello, Quang! I'm Luna.")).toBeVisible();
  await page.getByLabel('Your answer').fill('I live countryside.');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText('I live in the countryside. What do you like about it?')).toBeVisible();
  await expect(page.getByText(/repeat after me/i)).toHaveCount(0);
  await page.reload();
  await expect(page.getByText('I live in the countryside. What do you like about it?')).toBeVisible();
  await expect(page.getByText('Version').locator('..')).toContainText('1');
});

test('new session preserves the abandoned session in history', async ({ page }) => {
  await page.goto('/');
  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'New session' }).click();
  await expect(page.getByText('Session history')).toBeVisible();
  await expect(page.getByText(/abandoned/)).toBeVisible();
  await expect(page.getByText('Version').locator('..')).toContainText('0');
});
