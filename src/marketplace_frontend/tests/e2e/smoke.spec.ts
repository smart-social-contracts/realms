/**
 * Smoke tests for the marketplace_frontend SPA.
 *
 * These tests don't require a running marketplace_backend canister to
 * pass — they only verify that:
 *   - the page renders with the expected layout (nav, headings, footer);
 *   - the kind/metric toggles on Top Charts respond to clicks;
 *   - the upload page correctly gates on Internet Identity sign-in;
 *   - the my-purchases / developer pages also require sign-in.
 *
 * If a backend is reachable the Top Charts grid will populate; if not,
 * the spec still passes because we never assert presence of items.
 *
 * Set PLAYWRIGHT_BASE_URL to the deployed marketplace_frontend URL
 * before running, e.g.:
 *
 *   PLAYWRIGHT_BASE_URL=http://uzt4z-lp777-77774-qaabq-cai.localhost:4943 \
 *     npx playwright test
 */

import { expect, test } from '@playwright/test';

test.describe('marketplace_frontend smoke', () => {
  test('top charts page renders and toggles work', async ({ page }) => {
    await page.goto('/');

    // Header chrome
    await expect(page.getByRole('link', { name: /Realms Marketplace/i })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Top Charts' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Extensions' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Codices' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Upload' })).toBeVisible();

    // Page heading + subtitle
    await expect(page.getByRole('heading', { name: 'Top Charts' })).toBeVisible();
    await expect(page.getByText(/Discover the most popular extensions/i)).toBeVisible();

    // Both kind toggles present and switchable.
    await expect(page.getByRole('button', { name: /Extensions/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Codices/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Most Downloaded/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Most Liked/i })).toBeVisible();

    // Click 'Most Liked' — should not throw or navigate.
    await page.getByRole('button', { name: /Most Liked/i }).click();
    // Click 'Codices' kind toggle.
    await page.getByRole('button', { name: /Codices/i }).first().click();

    // Footer brand mark.
    await expect(page.getByText(/built on the/i)).toBeVisible();
  });

  test('extensions page renders search input, sort dropdown, and verified-only filter', async ({ page }) => {
    await page.goto('/extensions');
    await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible();
    await expect(page.getByPlaceholder('Search extensions…')).toBeVisible();
    await expect(page.getByText(/Verified only/i)).toBeVisible();
    // Sort dropdown with the three options the plan calls out.
    const sort = page.locator('select');
    await expect(sort).toBeVisible();
    const optionTexts = await sort.locator('option').allInnerTexts();
    expect(optionTexts).toEqual(expect.arrayContaining(['Newest', 'Most installs', 'Most likes']));
    // Switching sort should not throw.
    await sort.selectOption('installs');
    await sort.selectOption('likes');
  });

  test('codices page renders search input + sort dropdown', async ({ page }) => {
    await page.goto('/codices');
    await expect(page.getByRole('heading', { name: 'Codices' })).toBeVisible();
    await expect(page.getByPlaceholder('Search codices…')).toBeVisible();
    const sort = page.locator('select');
    await expect(sort).toBeVisible();
    const optionTexts = await sort.locator('option').allInnerTexts();
    expect(optionTexts).toEqual(expect.arrayContaining(['Newest', 'Most installs', 'Most likes']));
  });

  test('assistants page renders search input, domain + sort dropdowns', async ({ page }) => {
    await page.goto('/assistants');
    await expect(page.getByRole('heading', { name: 'AI Assistants' })).toBeVisible();
    await expect(page.getByPlaceholder('Search assistants…')).toBeVisible();
    // Domain + sort selects both present.
    const selects = page.locator('select');
    await expect(selects).toHaveCount(2);
  });

  test('top charts has Assistants kind toggle', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: /^Assistants$/ })).toBeVisible();
    await page.getByRole('button', { name: /^Assistants$/ }).click();
  });

  test('upload page gates on sign-in', async ({ page }) => {
    await page.goto('/upload');
    await expect(page.getByRole('heading', { name: 'Upload' })).toBeVisible();
    await expect(page.getByText(/Sign in required/i)).toBeVisible();
    await expect(
      page.getByText(/Anyone can upload — a developer license is only required to request an audit/i),
    ).toBeVisible();
  });

  test('my-purchases page gates on sign-in', async ({ page }) => {
    await page.goto('/my-purchases');
    await expect(page.getByRole('heading', { name: 'My Purchases' })).toBeVisible();
    await expect(page.getByText(/Sign in to view your purchases/i)).toBeVisible();
  });

  test('developer page gates on sign-in', async ({ page }) => {
    await page.goto('/developer');
    await expect(page.getByRole('heading', { name: 'Developer' })).toBeVisible();
    await expect(page.getByText(/Sign in required/i)).toBeVisible();
  });

  test('extension detail renders Overview/Files tabs (when listing exists)', async ({ page }) => {
    // Browse extensions and follow the first card if any exist; otherwise
    // skip — this makes the test backend-aware without hard-coding ids.
    await page.goto('/extensions');
    // Give the SPA a moment to fetch listings before deciding.
    await page.waitForTimeout(2500);
    const firstLink = page.locator('a.card').first();
    if ((await firstLink.count()) === 0) {
      test.skip(true, 'No extensions listed in this environment');
    }
    await firstLink.click();
    await expect(page.getByRole('tab', { name: 'Overview' })).toBeVisible();
    await expect(page.getByRole('tab', { name: /^Files/ })).toBeVisible();
    await page.getByRole('tab', { name: /^Files/ }).click();
    await expect(page.getByRole('tab', { name: /^Files/ })).toHaveAttribute('aria-selected', 'true');
  });
});
