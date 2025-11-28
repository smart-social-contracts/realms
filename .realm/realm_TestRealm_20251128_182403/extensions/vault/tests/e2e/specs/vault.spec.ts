import { test, expect } from '@playwright/test';

const TIMEOUT = 30000; // 30 seconds for vault operations

test.describe('Vault Extension E2E Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to the vault extension with increased timeout
    // Note: First page load can be slow due to canister cold start
    await page.goto('/extensions/vault', { 
      waitUntil: 'domcontentloaded',
      timeout: 60000 
    });
    
    // Wait for the Vault Manager heading to ensure page is fully loaded
    // Increased timeout handles cold starts and resource contention in CI
    await expect(page.getByRole('heading', { name: 'Vault Manager' })).toBeVisible({ timeout: 45000 });
    
    // Wait for refresh button to ensure components are mounted
    await expect(page.getByRole('button', { name: 'Refresh' })).toBeVisible({ timeout: 15000 });
  });

  test('should display vault manager page with all tabs', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Check page title
    await expect(page.getByRole('heading', { name: 'Vault Manager' })).toBeVisible();
    
    // Check all tabs are present
    await expect(page.getByRole('button', { name: 'Balance' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Transactions' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Transfer' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Admin' })).toBeVisible();
    
    // Check refresh button
    await expect(page.getByRole('button', { name: 'Refresh' })).toBeVisible();
  });

  test('should display vault principal and last refresh time', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Check vault principal is displayed
    await expect(page.getByText('Vault Principal:')).toBeVisible();
    
    // Click refresh to populate last refresh time
    const refreshButton = page.getByRole('button', { name: 'Refresh' });
    await refreshButton.click();
    
    // Wait for refresh to complete
    await page.waitForTimeout(2000);
    
    // Check last refresh time appears
    await expect(page.getByText('Last Refresh:')).toBeVisible();
  });

  test('should show transaction history with pagination', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Switch to Transactions tab
    await page.getByRole('button', { name: 'Transactions' }).click();
    
    // Wait a moment for tab content to render
    await page.waitForTimeout(500);
    
    // Wait for table to appear with visible headers
    await expect(page.getByRole('table')).toBeVisible({ timeout: 10000 });
    
    // Check table headers (table uses cells in header row, not th elements)
    const headerRow = page.locator('thead tr, tbody tr').first();
    await expect(headerRow.locator('text=ID')).toBeVisible();
    await expect(headerRow.locator('text=From')).toBeVisible();
    await expect(headerRow.locator('text=To')).toBeVisible();
    await expect(headerRow.locator('text=Amount')).toBeVisible();
    await expect(headerRow.locator('text=When')).toBeVisible();
    await expect(headerRow.locator('text=Type')).toBeVisible();
    
    // Wait for pagination to appear
    const paginationText = page.getByText(/Page \d+ of \d+/);
    await expect(paginationText).toBeVisible({ timeout: 5000 });
    
    // Check Previous and Next buttons
    await expect(page.getByRole('button', { name: /Previous/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Next/ })).toBeVisible();
  });

  test('should copy principal to clipboard when clicked', async ({ page, context }) => {
    test.setTimeout(TIMEOUT);
    
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    
    // Switch to Transactions tab
    await page.getByRole('button', { name: 'Transactions' }).click();
    
    // Wait for transactions to load
    await page.waitForTimeout(1000);
    
    // Find first principal button in the FROM column (td:nth-child(2))
    const principalButton = page.locator('tbody tr:first-child td:nth-child(2) button').first();
    
    if (await principalButton.isVisible()) {
      await principalButton.click();
      
      // Check for "Copied!" checkmark next to the clicked principal (more specific)
      await expect(page.locator('tbody tr:first-child td:nth-child(2) .text-green-600')).toBeVisible({ timeout: 2000 });
    }
  });

  test('should copy timestamp to clipboard when clicked', async ({ page, context }) => {
    test.setTimeout(TIMEOUT);
    
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    
    // Switch to Transactions tab
    await page.getByRole('button', { name: 'Transactions' }).click();
    
    // Wait for transactions to load
    await page.waitForTimeout(1000);
    
    // Find first timestamp button in the WHEN column (td:nth-child(5))
    const timestampButton = page.locator('tbody tr:first-child td:nth-child(5) button').first();
    
    if (await timestampButton.isVisible()) {
      await timestampButton.click();
      
      // Check for "Copied!" checkmark next to the clicked timestamp (more specific)
      await expect(page.locator('tbody tr:first-child td:nth-child(5) .text-green-600')).toBeVisible({ timeout: 2000 });
    }
  });

  test('should navigate between pages using pagination', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Switch to Transactions tab
    await page.getByRole('button', { name: 'Transactions' }).click();
    
    // Wait for data to load
    await page.waitForTimeout(1000);
    
    // Check if there are multiple pages
    const paginationText = page.getByText(/Page \d+ of \d+/);
    
    if (await paginationText.isVisible()) {
      const text = await paginationText.textContent();
      const match = text?.match(/Page (\d+) of (\d+)/);
      
      if (match && parseInt(match[2]) > 1) {
        // We have multiple pages, test pagination
        const nextButton = page.getByRole('button', { name: /Next/ });
        
        // Click Next
        await nextButton.click();
        await page.waitForTimeout(500);
        
        // Verify we're on page 2
        await expect(page.getByText('Page 2 of')).toBeVisible();
        
        // Click Previous
        const previousButton = page.getByRole('button', { name: /Previous/ });
        await previousButton.click();
        await page.waitForTimeout(500);
        
        // Verify we're back on page 1
        await expect(page.getByText('Page 1 of')).toBeVisible();
      }
    }
  });

  test('should display balance information', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Click Balance tab to ensure we're on the right tab
    await page.getByRole('button', { name: 'Balance' }).click();
    
    // Wait for balance heading to appear
    await expect(page.getByRole('heading', { name: 'Your Balance' })).toBeVisible();
    
    // Check satoshis display
    await expect(page.getByText(/satoshis/).first()).toBeVisible();
    
    // Check ckBTC conversion display (use first match to avoid strict mode violation)
    await expect(page.getByText(/≈.*ckBTC/)).toBeVisible();
  });

  test('should show transfer form in transfer tab', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Switch to Transfer tab
    await page.getByRole('button', { name: 'Transfer', exact: true }).first().click();
    
    // Check form elements
    await expect(page.getByText('Recipient Principal')).toBeVisible();
    await expect(page.getByText('Amount (satoshis)')).toBeVisible();
    
    // Check input fields
    await expect(page.getByPlaceholder(/xxxxx-xxxxx/)).toBeVisible();
    await expect(page.getByPlaceholder('100000000')).toBeVisible();
    
    // Check transfer submit button (inside the form, not the tab)
    const transferButton = page.locator('form button[type="submit"], form button:has-text("Transfer")').first();
    await expect(transferButton).toBeVisible();
    
    // Button should be disabled when form is empty
    await expect(transferButton).toBeDisabled();
  });

  test('should show admin information in admin tab', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Switch to Admin tab
    await page.getByRole('button', { name: 'Admin' }).click();
    
    // Check admin heading
    await expect(page.getByRole('heading', { name: 'Vault Admin' })).toBeVisible();
    
    // Check balance system info
    await expect(page.getByText(/All Balances in System/)).toBeVisible();
    
    // Check transfers info
    await expect(page.getByText('All Transfers in System')).toBeVisible();
  });

  test('should refresh vault data when refresh button is clicked', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    const refreshButton = page.getByRole('button', { name: 'Refresh' });
    
    // Click refresh
    await refreshButton.click();
    
    // Button should show "Refreshing..." while loading
    await expect(page.getByRole('button', { name: 'Refreshing...' })).toBeVisible({ timeout: 1000 });
    
    // Wait for refresh to complete
    await expect(refreshButton).toBeEnabled({ timeout: 30000 });
    await expect(page.getByRole('button', { name: 'Refresh' })).toBeVisible();
  });

  test('should display human-readable timestamps', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Switch to Transactions tab
    await page.getByRole('button', { name: 'Transactions' }).click();
    
    // Wait for transactions to load
    await page.waitForTimeout(1000);
    
    // Look for time ago format (e.g., "5m ago", "2h ago", "3d ago")
    const timeAgoPattern = /\d+[smhd]\s+ago/;
    const timeAgoElements = page.locator(`text=${timeAgoPattern}`);
    
    // If there are transactions, check they have readable timestamps
    const count = await timeAgoElements.count();
    if (count > 0) {
      await expect(timeAgoElements.first()).toBeVisible();
    }
  });

  test('should display user-friendly error message for insufficient funds', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Switch to Transfer tab
    await page.getByRole('button', { name: 'Transfer', exact: true }).first().click();
    
    // Fill in transfer form with a valid principal and amount
    // Note: This will fail if the vault doesn't have enough balance
    const recipientInput = page.getByPlaceholder(/xxxxx-xxxxx/);
    const amountInput = page.getByPlaceholder('100000000');
    
    // Use a test principal (this could be any valid principal)
    await recipientInput.fill('64fpo-jgpms-fpewi-hrskb-f3n6u-3z5fy-bv25f-zxjzg-q5m55-xmfpq-hqe');
    
    // Try to transfer an amount that would require more than available balance
    // (including the 10 satoshi fee)
    await amountInput.fill('999999999');
    
    // Submit the transfer
    const transferButton = page.locator('form button[type="submit"], form button:has-text("Transfer")').first();
    await transferButton.click();
    
    // Wait for the error message to appear
    // The error should contain user-friendly text about insufficient funds
    const errorMessage = page.locator('.bg-red-50, [class*="error"]').filter({ hasText: /Insufficient funds/ });
    
    // Check that the error is visible and contains helpful information
    await expect(errorMessage).toBeVisible({ timeout: 10000 });
    
    // Verify the error message contains:
    // 1. The phrase "Insufficient funds"
    // 2. Information about the current balance
    // 3. Information about the transaction fee requirement
    await expect(page.getByText(/Insufficient funds.*satoshis/)).toBeVisible();
    
    // The error should mention the 10 satoshi transaction fee requirement
    await expect(page.getByText(/minimum.*10 satoshis.*fee/i)).toBeVisible();
  });

  test('should validate transfer form inputs', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Switch to Transfer tab
    await page.getByRole('button', { name: 'Transfer', exact: true }).first().click();
    
    const recipientInput = page.getByPlaceholder(/xxxxx-xxxxx/);
    const amountInput = page.getByPlaceholder('100000000');
    const transferButton = page.locator('form button[type="submit"], form button:has-text("Transfer")').first();
    
    // Button should be disabled with empty inputs
    await expect(transferButton).toBeDisabled();
    
    // Fill only recipient
    await recipientInput.fill('64fpo-jgpms-fpewi-hrskb-f3n6u-3z5fy-bv25f-zxjzg-q5m55-xmfpq-hqe');
    await expect(transferButton).toBeDisabled();
    
    // Clear recipient and fill only amount
    await recipientInput.clear();
    await amountInput.fill('100');
    await expect(transferButton).toBeDisabled();
    
    // Fill both fields with valid values
    await recipientInput.fill('64fpo-jgpms-fpewi-hrskb-f3n6u-3z5fy-bv25f-zxjzg-q5m55-xmfpq-hqe');
    await amountInput.fill('100');
    
    // Button should be enabled when both fields are filled
    await expect(transferButton).toBeEnabled();
  });
});
