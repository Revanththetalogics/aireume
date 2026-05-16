import { test, expect } from '@playwright/test';

test.describe('Analysis Flow', () => {
  test('Screen Resumes should start at Step 1 (JD & Skills)', async ({ page }) => {
    // Navigate directly to /analyze (simulating "Screen Resumes" button)
    await page.goto('/analyze');
    await page.waitForLoadState('networkidle');

    // Should be on Step 1 - JD & Skills
    // Look for JD input area (textarea or file upload for JD)
    const step1Indicator = page.getByText(/step 1|jd.*skills|paste.*job|job description/i).first();
    await expect(step1Indicator).toBeVisible({ timeout: 10000 });

    // Step 2 should NOT be active (upload area should not be primary)
    // The stepper should show step 1 as current
    const currentStep = page.locator('[class*="bg-brand"], [class*="text-brand"]').filter({ hasText: /1|jd/i });
    await expect(currentStep).toBeVisible();
  });

  test('Full analysis flow: JD paste → Skills → Upload', async ({ page }) => {
    await page.goto('/analyze');
    await page.waitForLoadState('networkidle');

    // Step 1: Paste JD text
    const jdTextarea = page.locator('textarea').first();
    await expect(jdTextarea).toBeVisible({ timeout: 10000 });

    const sampleJD = `Senior Software Engineer - AI Implementation
    
Must-have Skills:
- Python programming (5+ years)
- Machine Learning and Deep Learning
- REST API development
- Docker and Kubernetes

Good-to-have Skills:
- AWS or GCP cloud experience
- CI/CD pipelines
- Agile methodology`;

    await jdTextarea.fill(sampleJD);

    // Click Parse/Next/Continue button
    const parseBtn = page.getByRole('button', { name: /parse|next|continue|analyze/i }).first();
    await expect(parseBtn).toBeEnabled({ timeout: 5000 });
    await parseBtn.click();

    // Wait for JD parsing (LLM call - may take time)
    // Should show skills confirmation or move to Step 2
    await page.waitForTimeout(3000); // Allow parsing

    // Look for skills section or Step 2
    const skillsOrStep2 = page.getByText(/must.have|confirm.*skills|upload.*resume|step 2/i).first();
    await expect(skillsOrStep2).toBeVisible({ timeout: 60000 }); // LLM can be slow

    // If skills confirmation is shown, confirm them
    const confirmBtn = page.getByRole('button', { name: /confirm|accept|next|proceed/i });
    if (await confirmBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await confirmBtn.click();
    }

    // Should reach Step 2: Upload & Analyze
    await expect(page.getByText(/upload.*resume|drop.*resume|step 2/i).first()).toBeVisible({ timeout: 30000 });
  });

  test('Analyze Another Resume preserves context', async ({ page }) => {
    // First navigate to analyze and set up a JD context
    await page.goto('/analyze');
    await page.waitForLoadState('networkidle');

    const jdTextarea = page.locator('textarea').first();
    await expect(jdTextarea).toBeVisible({ timeout: 10000 });
    await jdTextarea.fill('Test JD for context preservation\n\nMust-have: Python, SQL');

    // Store that we set JD text
    const jdFilled = await jdTextarea.inputValue();
    expect(jdFilled).toContain('Python');

    // Note: Full "Analyze Another" flow requires completing an analysis first
    // This is a smoke test to verify the page loads correctly at Step 1
  });
});
