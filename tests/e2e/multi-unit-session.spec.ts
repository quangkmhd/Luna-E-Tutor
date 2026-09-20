import { expect, test } from '@playwright/test';

test('selects, persists, and renders Unit 2 without Unit 1 content', async ({
  page,
  request,
}) => {
  await page.goto('/');
  await page.getByRole(
    'button', { name: /Unit 2.*Our homes/i },
  ).click();

  await expect(page.getByText('Our homes')).toBeVisible();
  await expect(page.getByText('English Tutor · Unit 2')).toBeVisible();
  await expect(page.getByText('All about me!')).toHaveCount(0);

  await page.getByLabel('Your answer').fill('I feel happy.');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText(
    'Thank you, Quang. Tell me a little more?',
  )).toBeVisible();

  const sessions = await (
    await request.get('http://localhost:8091/api/sessions')
  ).json();
  const unit2 = sessions.find(
    (session: { unit_id: string }) => session.unit_id === 'grade05.unit02',
  );
  expect(unit2).toBeTruthy();
  expect(unit2.unit.title).toBe('Our homes');

  await page.reload();
  await expect(page.getByRole(
    'heading', { name: 'Choose a unit' },
  )).toBeVisible();
  const persisted = await (
    await request.get(
      `http://localhost:8091/api/sessions/${unit2.session_id}`,
    )
  ).json();
  expect(persisted.unit_id).toBe('grade05.unit02');
  expect(persisted.unit.title).toBe('Our homes');
});

test('opens Unit 2 directly at its canonical URL and returns to the selector', async ({ page }) => {
  await page.goto('/unit2');

  await expect(page).toHaveURL(/\/unit2$/);
  await expect(page.getByText('English Tutor · Unit 2')).toBeVisible();
  await expect(page.getByText('Our homes')).toBeVisible();
  await expect(page.getByText('All about me!')).toHaveCount(0);

  await page.getByRole('button', { name: 'Choose another unit' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: 'Choose a unit' })).toBeVisible();
});
