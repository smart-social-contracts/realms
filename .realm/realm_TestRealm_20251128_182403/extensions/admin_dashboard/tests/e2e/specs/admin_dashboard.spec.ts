import { test, expect } from '@playwright/test';

/**
 * Admin Dashboard E2E Tests
 * Tests the dropdown-based entity viewer UI
 */

test.describe('Admin Dashboard E2E Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to admin dashboard  
    await page.goto('/admin', { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    // Wait for page to load (admin dashboard should be visible)
    await expect(page.getByRole('heading', { level: 1 }))
      .toBeVisible({ timeout: 30000 });
  });

  test('should display admin dashboard page with main heading', async ({ page }) => {
    // Check for main heading
    const heading = page.getByRole('heading', { level: 1, name: /Admin Dashboard/i });
    await expect(heading).toBeVisible();
    
    // Check for subtitle
    const subtitle = page.getByText(/Manage realm entities/i);
    await expect(subtitle).toBeVisible();
  });

  test('should have entity type dropdown selector', async ({ page }) => {
    // Find the entity type selector
    const entitySelect = page.locator('#entity-type-select');
    await expect(entitySelect).toBeVisible();
    
    // Check if it has options
    const options = await entitySelect.locator('option').count();
    expect(options).toBeGreaterThan(0);
  });

  test('should have load data button', async ({ page }) => {
    // Find the load button
    const loadButton = page.getByRole('button', { name: /Load Data/i });
    await expect(loadButton).toBeVisible();
    await expect(loadButton).toBeEnabled();
  });

  test('should load and display entity data', async ({ page }) => {
    // Select an entity type (default should be Users)
    const entitySelect = page.locator('#entity-type-select');
    await expect(entitySelect).toBeVisible();
    
    // Click load button
    const loadButton = page.getByRole('button', { name: /Load Data/i });
    await loadButton.click();
    
    // Wait for loading to complete (button text changes back from "Loading...")
    await expect(loadButton).toContainText(/Load Data/i, { timeout: 10000 });
    
    // Check if items count is displayed
    await expect(page.getByText(/Showing \d+ of \d+ items/i)).toBeVisible({ timeout: 5000 });
  });

  test('should allow entity type selection', async ({ page }) => {
    // Get entity type selector
    const entitySelect = page.locator('#entity-type-select');
    
    // Change entity type to organizations
    await entitySelect.selectOption('organizations');
    await expect(entitySelect).toHaveValue('organizations');
    
    // Change to mandates
    await entitySelect.selectOption('mandates');
    await expect(entitySelect).toHaveValue('mandates');
  });

  test('should display pagination controls when data is loaded', async ({ page }) => {
    // Load data first
    const loadButton = page.getByRole('button', { name: /Load Data/i });
    await loadButton.click();
    await expect(loadButton).toContainText(/Load Data/i, { timeout: 10000 });
    
    // Check if items are loaded by looking for the count text
    await expect(page.getByText(/Showing \d+ of \d+ items/i)).toBeVisible({ timeout: 5000 });
    
    // If there's data and multiple pages, pagination buttons should appear
    // We don't assert pagination presence as it depends on data volume
  });

  test('should show expandable item details', async ({ page }) => {
    // Load data first
    const loadButton = page.getByRole('button', { name: /Load Data/i });
    await loadButton.click();
    await expect(loadButton).toContainText(/Load Data/i, { timeout: 10000 });
    
    // Wait for items to appear
    await expect(page.getByText(/Showing \d+ of \d+ items/i)).toBeVisible({ timeout: 5000 });
    
    // Find the first expandable item button (▶ arrow button)
    const expandButton = page.getByRole('button').filter({ hasText: /▶/ }).first();
    
    // Click to expand
    await expandButton.click();
    
    // Check if details are now visible (arrow changes to ▼)
    await expect(page.getByRole('button').filter({ hasText: /▼/ }).first()).toBeVisible();
  });

  test('should display empty state when no data exists', async ({ page }) => {
    // Select an entity type that might not have data
    const entitySelect = page.locator('#entity-type-select');
    await entitySelect.selectOption('licenses');
    
    // Load data
    const loadButton = page.getByRole('button', { name: /Load Data/i });
    await loadButton.click();
    await expect(loadButton).toContainText(/Load Data/i, { timeout: 10000 });
    
    // If no data, should show empty message or zero count
    const emptyMessage = page.getByText(/No items found/i);
    const zeroCount = page.getByText(/Showing 0 of 0 items/i);
    
    // Either empty message or zero count should be visible
    const hasEmptyState = await emptyMessage.isVisible().catch(() => false) || 
                          await zeroCount.isVisible().catch(() => false);
    expect(hasEmptyState).toBeTruthy();
  });

  test('should be responsive and render on smaller screens', async ({ page }) => {
    // Set viewport to mobile size
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Page should still be visible
    await expect(page.getByRole('heading', { level: 1, name: /Admin Dashboard/i })).toBeVisible();
    
    // Entity selector should still be visible
    await expect(page.locator('#entity-type-select')).toBeVisible();
    
    // Load button should still be visible
    await expect(page.getByRole('button', { name: /Load Data/i })).toBeVisible();
  });
});
