import { test, expect } from '@playwright/test';

test.describe('Requisitions', () => {
  test('requisitions list page loads', async ({ page }) => {
    await page.goto('/requisitions');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /requisitions|my openings/i })).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByText(/calibrated openings|approve intake|hm intake/i).first()).toBeVisible();
  });

  test('can create a requisition and open detail', async ({ page }) => {
    await page.goto('/requisitions');
    await page.waitForLoadState('networkidle');

    const createBtn = page.getByRole('button', { name: /new requisition/i });
    await expect(createBtn).toBeVisible({ timeout: 15000 });
    await createBtn.click();

    const uniqueTitle = `E2E QA Engineer ${Date.now()}`;
    const jdText = [
      'Senior QA Automation Engineer responsible for end-to-end test strategy.',
      'Must-have: Playwright, Python, CI/CD pipelines, API testing, SQL.',
      'Good-to-have: Docker, Kubernetes, performance testing, accessibility audits.',
      'You will design regression suites, maintain staging smoke tests, and partner',
      'with engineering on release quality gates across multiple product surfaces.',
    ].join(' ');

    await page.getByText('Title', { exact: true }).locator('..').locator('input').fill(uniqueTitle);
    await page.getByText('Job description', { exact: true }).locator('..').locator('textarea').fill(jdText);
    await page.getByRole('button', { name: /^create$/i }).click();

    await expect(page).toHaveURL(/\/requisitions\/\d+/, { timeout: 20000 });
    await expect(page.getByRole('heading', { name: uniqueTitle })).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole('button', { name: /calibrate/i })).toBeVisible();
  });

  test('requisition detail tabs are navigable', async ({ page }) => {
    await page.goto('/requisitions');
    await page.waitForLoadState('networkidle');

    const firstCard = page.locator('a[href^="/requisitions/"]').first();
    if (!(await firstCard.isVisible({ timeout: 10000 }).catch(() => false))) {
      test.skip();
      return;
    }
    await firstCard.click();
    await expect(page).toHaveURL(/\/requisitions\/\d+/);

    for (const tab of [/overview/i, /intake/i, /criteria/i, /pipeline/i]) {
      const tabBtn = page.getByRole('button', { name: tab });
      if (await tabBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await tabBtn.click();
        await expect(tabBtn).toBeVisible();
      }
    }
  });

  test('screen candidate CTA opens analyze with requisition context', async ({ page }) => {
    await page.goto('/requisitions');
    await page.waitForLoadState('networkidle');

    const firstCard = page.locator('a[href^="/requisitions/"]').first();
    if (!(await firstCard.isVisible({ timeout: 10000 }).catch(() => false))) {
      test.skip();
      return;
    }
    const href = await firstCard.getAttribute('href');
    const reqId = href?.match(/\/requisitions\/(\d+)/)?.[1];
    if (!reqId) {
      test.skip();
      return;
    }

    await page.goto(`/requisitions/${reqId}`);
    const screenBtn = page.getByRole('button', { name: /screen candidate/i });
    if (!(await screenBtn.isVisible({ timeout: 10000 }).catch(() => false))) {
      test.skip();
      return;
    }
    await screenBtn.click();

    await expect(page).toHaveURL(new RegExp(`/analyze\\?requisition_id=${reqId}`));
    await expect(page.getByRole('button', { name: /load from requisitions/i })).toBeVisible({
      timeout: 15000,
    });
  });
});

test.describe('Legacy route redirects', () => {
  test('/jd-library redirects to requisitions', async ({ page }) => {
    await page.goto('/jd-library');
    await expect(page).toHaveURL(/\/requisitions/, { timeout: 15000 });
  });

  test('/projects redirects to requisitions', async ({ page }) => {
    await page.goto('/projects');
    await expect(page).toHaveURL(/\/requisitions/, { timeout: 15000 });
  });

  test('/jd-library/:id redirects to requisition detail', async ({ page }) => {
    await page.goto('/requisitions');
    await page.waitForLoadState('networkidle');

    const firstCard = page.locator('a[href^="/requisitions/"]').first();
    if (!(await firstCard.isVisible({ timeout: 10000 }).catch(() => false))) {
      test.skip();
      return;
    }
    const href = await firstCard.getAttribute('href');
    const reqId = href?.match(/\/requisitions\/(\d+)/)?.[1];
    if (!reqId) {
      test.skip();
      return;
    }

    await page.goto(`/jd-library/${reqId}`);
    await expect(page).toHaveURL(new RegExp(`/requisitions/${reqId}$`));
  });

  test('/jd-library/:id/candidates redirects to pipeline tab', async ({ page }) => {
    await page.goto('/requisitions');
    await page.waitForLoadState('networkidle');

    const firstCard = page.locator('a[href^="/requisitions/"]').first();
    if (!(await firstCard.isVisible({ timeout: 10000 }).catch(() => false))) {
      test.skip();
      return;
    }
    const href = await firstCard.getAttribute('href');
    const reqId = href?.match(/\/requisitions\/(\d+)/)?.[1];
    if (!reqId) {
      test.skip();
      return;
    }

    await page.goto(`/jd-library/${reqId}/candidates`);
    await expect(page).toHaveURL(new RegExp(`/requisitions/${reqId}\\?tab=pipeline`));
  });
});
