import { expect, test } from '@playwright/test';

test('opens standalone Free Talk, chooses a topic, and returns without finishing Unit 1', async ({ page }) => {
  const finishRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/finish')) finishRequests.push(request.url());
  });

  await page.goto('/talk');
  for (const topic of ['My hobbies', 'My family', 'School life', 'Food', 'Animals', 'Travel']) {
    await expect(page.getByRole('button', { name: topic })).toBeVisible();
  }
  await expect(page.getByRole('button', { name: 'Start Free Talk' })).toBeDisabled();
  await page.getByRole('button', { name: 'Animals' }).click();
  await page.getByRole('button', { name: 'Start Free Talk' }).click();
  await expect(page.getByText('Talking about Animals')).toBeVisible();

  await page.getByRole('link', { name: 'Back to Unit 1' }).click();
  await expect(page.getByRole('heading', { name: 'Choose a unit' })).toBeVisible();
  await page.getByRole('button', { name: /Unit 1.*All about me!/i }).click();
  await expect(page.getByRole('heading', { name: 'Practice with Luna' })).toBeVisible();
  expect(finishRequests).toEqual([]);
});
