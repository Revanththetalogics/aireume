import { test, expect } from '@playwright/test';
import {
  enableAdHocScreeningIfAvailable,
  expectRequisitionPicker,
  gotoAnalyze,
  selectFirstRequisitionOnAnalyze,
} from './helpers';

/**
 * End-to-end recruiter flow: requisition → analyze entry point.
 * Complements analysis-flow.spec.ts with requisition-first vocabulary.
 */
test.describe('Requisition-first analyze flow', () => {
  test('analyze page uses requisition picker vocabulary', async ({ page }) => {
    await gotoAnalyze(page);

    await expect(page.getByText(/step 1.*opening|opening.*skill|job description/i).first()).toBeVisible({
      timeout: 15000,
    });
    await expectRequisitionPicker(page);
  });

  test('analyze loads requisition from query param', async ({ page }) => {
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

    await page.goto(`/analyze?requisition_id=${reqId}`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByText(/screening for/i).first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/job description/i).first()).toBeVisible({ timeout: 15000 });
  });

  test('full analyze step 1: ad-hoc paste JD → skills gate when allowed', async ({ page }) => {
    await gotoAnalyze(page);

    const adHocEnabled = await enableAdHocScreeningIfAvailable(page);
    if (!adHocEnabled) {
      const selected = await selectFirstRequisitionOnAnalyze(page);
      if (!selected) {
        test.skip();
        return;
      }
      await expect(page.getByText(/must.have|confirm.*skills|upload.*resume|step 2|skills loaded/i).first())
        .toBeVisible({ timeout: 90000 });
      return;
    }

    const jdTextarea = page.locator('textarea').first();
    const sampleJD = `Senior Software Engineer - Platform

Must-have Skills:
- Python programming (5+ years)
- Machine Learning and API design
- Docker and Kubernetes
- PostgreSQL and distributed systems

Good-to-have Skills:
- AWS or GCP cloud experience
- CI/CD pipelines and observability
- Agile delivery with cross-functional teams`;

    await jdTextarea.fill(sampleJD);

    const parseBtn = page.getByRole('button', { name: /parse|next|continue|review skills/i }).first();
    if (await parseBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await parseBtn.click();
    }

    const skillsOrStep2 = page.getByText(/must.have|confirm.*skills|upload.*resume|step 2/i).first();
    await expect(skillsOrStep2).toBeVisible({ timeout: 90000 });
  });
});
