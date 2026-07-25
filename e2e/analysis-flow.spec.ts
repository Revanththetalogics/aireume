import { test, expect } from '@playwright/test';
import {
  enableAdHocScreeningIfAvailable,
  expectRequisitionPicker,
  gotoAnalyze,
  selectFirstRequisitionOnAnalyze,
} from './helpers';

test.describe('Analysis Flow', () => {
  test('Screen Resumes should start at Step 1 (Opening & skills)', async ({ page }) => {
    await gotoAnalyze(page);

    await expect(page.getByText(/step 1|opening.*skills|job description/i).first()).toBeVisible({
      timeout: 10000,
    });
    await expectRequisitionPicker(page);
  });

  test('Full analysis flow: requisition → skills → upload', async ({ page }) => {
    const selected = await selectFirstRequisitionOnAnalyze(page);
    if (!selected) {
      test.skip();
      return;
    }

    const skillsOrStep2 = page.getByText(/must.have|confirm.*skills|upload.*resume|step 2|skills loaded/i).first();
    await expect(skillsOrStep2).toBeVisible({ timeout: 60000 });

    const confirmBtn = page.getByRole('button', { name: /confirm|accept|next|proceed|continue/i });
    if (await confirmBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await confirmBtn.click();
    }

    await expect(page.getByText(/upload.*resume|drop.*resume|step 2/i).first()).toBeVisible({
      timeout: 30000,
    });
  });

  test('Ad-hoc JD paste flow when tenant allows it', async ({ page }) => {
    await gotoAnalyze(page);

    const adHocEnabled = await enableAdHocScreeningIfAvailable(page);
    if (!adHocEnabled) {
      test.skip();
      return;
    }

    const jdTextarea = page.locator('textarea').first();
    await jdTextarea.fill('Test JD for context preservation\n\nMust-have: Python, SQL');
    await expect(jdTextarea).toHaveValue(/Python/);
  });
});
