import { expect, test } from '@playwright/test';

test('opens Grade 3 and completes a scripted lesson through Text', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Lớp 3/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Lớp 5/ })).toHaveCount(0);
  await page.getByRole('button', { name: /Unit 1.*Hello/i }).click();
  await expect(page).toHaveURL(/\/grade3\/unit1$/);
  await page.getByRole('link', { name: /Lesson 1.*Greetings/i }).click();
  await expect(page.getByText('Say hello to Luna.')).toBeVisible();
  await page.getByLabel('Your answer').fill('Hello, Luna!');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText('Great work today!')).toBeVisible();
  await expect(page.getByText('completed')).toBeVisible();
});
