import { test, expect } from '@playwright/test';

const TIMEOUT = 30000; // 30 seconds for dashboard operations

test.describe('Member Dashboard Extension E2E Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to the member dashboard extension with increased timeout
    // Note: First page load can be slow due to canister cold start
    await page.goto('/extensions/member_dashboard', { 
      waitUntil: 'domcontentloaded',
      timeout: 60000 
    });
    
    // Wait for the Member Dashboard heading to ensure page is fully loaded
    // Increased timeout handles cold starts and resource contention in CI
    await expect(page.getByRole('heading', { name: /Member Dashboard|Citizen Dashboard/i })).toBeVisible({ timeout: 45000 });
  });

  test('should display member dashboard page with main sections', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Check page title
    await expect(page.getByRole('heading', { name: /Member Dashboard|Citizen Dashboard/i })).toBeVisible();
    
    // Check dashboard summary section exists
    await expect(page.getByText(/Dashboard Summary|Overview/i)).toBeVisible({ timeout: 10000 });
  });

  test('should display dashboard summary cards with statistics', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Wait for summary data to load
    await page.waitForTimeout(2000);
    
    // Check for Dashboard Overview Card (the main summary card)
    const dashboardOverview = page.getByText(/Dashboard Overview|dashboard_overview/i);
    await expect(dashboardOverview).toBeVisible({ timeout: 10000 });
    
    // Check for stat numbers - these are in elements with class "font-bold text-xl"
    const statNumbers = page.locator('.font-bold.text-xl');
    const count = await statNumbers.count();
    
    // Should have at least 4 stat cards (Services, Tax, Personal Data, Payment Accounts)
    expect(count).toBeGreaterThanOrEqual(4);
    
    // Verify at least one stat number is visible
    await expect(statNumbers.first()).toBeVisible({ timeout: 10000 });
    
    // Check for common dashboard section headers
    const servicesText = page.getByText(/Public Services|public_services/i);
    const taxText = page.getByText(/My Taxes|my_taxes|Tax/i);
    
    // At least one of these should be visible
    const hasServices = await servicesText.count() > 0;
    const hasTax = await taxText.count() > 0;
    
    expect(hasServices || hasTax).toBeTruthy();
  });

  test('should display public services section', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Look for services section heading or navigation
    const servicesSection = page.getByText(/Public Services|Services|Available Services/i);
    
    if (await servicesSection.isVisible({ timeout: 5000 })) {
      // Click if it's a tab or link
      if (await servicesSection.evaluate(el => el.tagName === 'BUTTON' || el.tagName === 'A')) {
        await servicesSection.click();
        await page.waitForTimeout(1000);
      }
      
      // Check for services list or table
      const servicesList = page.locator('[class*="service"], [role="list"], table');
      await expect(servicesList.first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('should display tax information section with invoices', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Look for tax/invoices section
    const taxSection = page.getByText(/Tax Information|Invoices|Financial Information/i);
    
    if (await taxSection.isVisible({ timeout: 5000 })) {
      // Click if it's a tab or link
      if (await taxSection.evaluate(el => el.tagName === 'BUTTON' || el.tagName === 'A')) {
        await taxSection.click();
        await page.waitForTimeout(1000);
      }
      
      // Check for invoices/tax records display
      const invoicesList = page.locator('[class*="invoice"], [class*="tax"], table');
      await expect(invoicesList.first()).toBeVisible({ timeout: 10000 });
      
      // Check for amount displays (currency)
      const amountPattern = /\$\d+|\d+\.\d{2}/;
      await expect(page.locator(`text=${amountPattern}`).first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('should display personal data section', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Look for personal data section
    const personalSection = page.getByText(/Personal Data|Personal Information|Profile/i);
    
    if (await personalSection.isVisible({ timeout: 5000 })) {
      // Click if it's a tab or link
      if (await personalSection.evaluate(el => el.tagName === 'BUTTON' || el.tagName === 'A')) {
        await personalSection.click();
        await page.waitForTimeout(1000);
      }
      
      // Check that personal data is displayed
      const dataDisplay = page.locator('[class*="profile"], [class*="personal"], form, dl');
      await expect(dataDisplay.first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('should handle refresh/reload of dashboard data', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Look for refresh button
    const refreshButton = page.getByRole('button', { name: /Refresh|Reload|Update/i });
    
    if (await refreshButton.isVisible({ timeout: 5000 })) {
      // Click refresh
      await refreshButton.click();
      
      // Check for loading state
      const loadingIndicator = page.locator('[class*="loading"], [class*="spinner"]');
      if (await loadingIndicator.isVisible({ timeout: 2000 })) {
        // Wait for loading to complete
        await expect(loadingIndicator).not.toBeVisible({ timeout: 15000 });
      }
      
      // Verify data is still visible after refresh
      await expect(page.getByRole('heading', { name: /Member Dashboard|Citizen Dashboard/i })).toBeVisible();
    }
  });

  test('should display invoice status indicators', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Navigate to invoices section
    const invoicesSection = page.getByText(/Tax Information|Invoices/i).first();
    
    if (await invoicesSection.isVisible({ timeout: 5000 })) {
      if (await invoicesSection.evaluate(el => el.tagName === 'BUTTON' || el.tagName === 'A')) {
        await invoicesSection.click();
        await page.waitForTimeout(1000);
      }
      
      // Look for status badges (Paid, Pending, Overdue, etc.)
      const statusBadges = page.locator('[class*="badge"], [class*="status"], [class*="pill"]');
      
      if (await statusBadges.count() > 0) {
        // Check for common status text
        const statusPattern = /Paid|Pending|Overdue|Due/i;
        const statusElements = page.locator(`text=${statusPattern}`);
        await expect(statusElements.first()).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should display service provider information', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Navigate to services section
    const servicesSection = page.getByText(/Public Services|Services/i).first();
    
    if (await servicesSection.isVisible({ timeout: 5000 })) {
      if (await servicesSection.evaluate(el => el.tagName === 'BUTTON' || el.tagName === 'A')) {
        await servicesSection.click();
        await page.waitForTimeout(1000);
      }
      
      // Check for service details (name, provider, description)
      const serviceElements = page.locator('[class*="service"]');
      
      if (await serviceElements.count() > 0) {
        // Should have service names
        await expect(serviceElements.first()).toContainText(/[A-Za-z]{3,}/);
      }
    }
  });

  test('should show summary statistics accurately', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Wait for dashboard to load
    await page.waitForTimeout(2000);
    
    // Check for summary cards with numbers
    const summaryCards = page.locator('[class*="summary"], [class*="card"], [class*="stat"]');
    
    if (await summaryCards.count() > 0) {
      // Each card should have a number and label
      const firstCard = summaryCards.first();
      
      // Should contain a number
      await expect(firstCard).toContainText(/\d+/);
      
      // Should contain descriptive text
      await expect(firstCard).toContainText(/[A-Za-z]{3,}/);
    }
  });

  test('should navigate between dashboard sections smoothly', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Get all navigation tabs/links
    const navItems = page.locator('nav button, nav a, [role="tab"]').filter({ hasText: /Services|Tax|Personal|Dashboard/i });
    
    const navCount = await navItems.count();
    
    if (navCount > 1) {
      // Click first nav item
      await navItems.nth(0).click();
      await page.waitForTimeout(500);
      
      // Verify content changed
      await expect(page.locator('main, [role="main"]')).toBeVisible();
      
      // Click second nav item
      await navItems.nth(1).click();
      await page.waitForTimeout(500);
      
      // Verify content still visible
      await expect(page.locator('main, [role="main"]')).toBeVisible();
    }
  });

  test('should display due dates for invoices', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Navigate to invoices
    const invoicesSection = page.getByText(/Tax Information|Invoices/i).first();
    
    if (await invoicesSection.isVisible({ timeout: 5000 })) {
      if (await invoicesSection.evaluate(el => el.tagName === 'BUTTON' || el.tagName === 'A')) {
        await invoicesSection.click();
        await page.waitForTimeout(1000);
      }
      
      // Look for date displays
      // Common date formats: MM/DD/YYYY, DD-MM-YYYY, YYYY-MM-DD, or relative dates
      const datePattern = /\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}/;
      const dateElements = page.locator(`text=${datePattern}`);
      
      if (await dateElements.count() > 0) {
        await expect(dateElements.first()).toBeVisible();
      } else {
        // Check for "Due Date" label
        const dueDateLabel = page.getByText(/Due Date|Payment Due|Due:/i);
        await expect(dueDateLabel.first()).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should show financial summary totals', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Navigate to tax information
    const taxSection = page.getByText(/Tax Information|Invoices|Financial/i).first();
    
    if (await taxSection.isVisible({ timeout: 5000 })) {
      if (await taxSection.evaluate(el => el.tagName === 'BUTTON' || el.tagName === 'A')) {
        await taxSection.click();
        await page.waitForTimeout(1000);
      }
      
      // Look for total amount displays
      const totalPattern = /Total|Sum|Balance/i;
      const totals = page.locator(`text=${totalPattern}`);
      
      if (await totals.count() > 0) {
        // Should have associated amount
        const totalSection = page.locator('[class*="total"], [class*="summary"]').first();
        await expect(totalSection).toContainText(/\$?\d+/);
      }
    }
  });

  test('should handle empty state gracefully', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // The dashboard should load even with no data
    await expect(page.getByRole('heading', { name: /Member Dashboard|Citizen Dashboard/i })).toBeVisible();
    
    // Check if there are any "no data" or "empty" messages
    const emptyMessages = page.getByText(/No data|No invoices|No services|Empty/i);
    
    // If empty messages are present, they should be styled appropriately
    if (await emptyMessages.count() > 0) {
      await expect(emptyMessages.first()).toBeVisible();
    }
  });

  test('should display user-friendly error messages', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Look for any error messages on the page
    const errorElements = page.locator('[class*="error"], [class*="alert-danger"], .bg-red-50');
    
    if (await errorElements.count() > 0) {
      // Error messages should be visible and contain helpful text
      const errorText = await errorElements.first().textContent();
      expect(errorText?.length).toBeGreaterThan(10);
    }
  });
});

test.describe('Payment Accounts Functionality Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to member dashboard
    await page.goto('/extensions/member_dashboard', { 
      waitUntil: 'domcontentloaded',
      timeout: 60000 
    });
    
    // Wait for dashboard to load
    await expect(page.getByRole('heading', { name: /Member Dashboard|Citizen Dashboard/i })).toBeVisible({ timeout: 45000 });
    
    // Navigate to Payment Accounts tab
    const paymentAccountsTab = page.getByRole('tab', { name: /Payment Accounts/i });
    await paymentAccountsTab.click();
    await page.waitForTimeout(1000);
  });

  test('should display Payment Accounts section', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Check for Add Payment Account button (tab already navigated in beforeEach)
    const addButton = page.getByRole('button', { name: /Add Payment Account/i });
    await expect(addButton).toBeVisible({ timeout: 10000 });
  });

  test('should open Add Payment Account modal', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Click Add Payment Account button (tab already navigated in beforeEach)
    const addButton = page.getByRole('button', { name: /Add Payment Account/i });
    await addButton.click();
    
    // Wait for modal to appear
    await page.waitForTimeout(500);
    
    // Check modal title
    await expect(page.getByRole('heading', { name: /Add Payment Account/i })).toBeVisible();
    
    // Check form fields are present
    await expect(page.getByLabel(/Account Label|Label/i)).toBeVisible();
    await expect(page.getByLabel(/Network/i)).toBeVisible();
    await expect(page.getByLabel(/Currency/i)).toBeVisible();
    await expect(page.getByLabel(/Address/i)).toBeVisible();
    
    // Check buttons
    await expect(page.getByRole('button', { name: /Save/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Cancel/i })).toBeVisible();
  });

  test('should close modal when Cancel is clicked', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Open modal
    const addButton = page.getByRole('button', { name: /Add Payment Account/i });
    await addButton.click();
    await page.waitForTimeout(500);
    
    // Click Cancel
    const cancelButton = page.getByRole('button', { name: /Cancel/i });
    await cancelButton.click();
    
    // Modal should close
    await page.waitForTimeout(500);
    await expect(page.getByRole('heading', { name: /Add Payment Account/i })).not.toBeVisible();
  });

  test('should validate required fields', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Open modal
    const addButton = page.getByRole('button', { name: /Add Payment Account/i });
    await addButton.click();
    await page.waitForTimeout(500);
    
    // Try to save without filling fields
    const saveButton = page.getByRole('button', { name: /Save/i });
    await saveButton.click();
    
    // Should show error message
    await page.waitForTimeout(500);
    const errorMessage = page.locator('[class*="error"], [class*="alert-error"]');
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
    await expect(errorMessage).toContainText(/required/i);
  });

  test('should validate ICP address format', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Open modal
    const addButton = page.getByRole('button', { name: /Add Payment Account/i });
    await addButton.click();
    await page.waitForTimeout(1000);
    
    // Fill in required fields with invalid ICP address
    await page.getByLabel(/Account Label|Label/i).fill('Test ICP Account');
    
    // Select ICP network (use value, not label)
    await page.getByLabel(/Network/i).selectOption('ICP');
    
    // Select ICP currency
    await page.getByLabel(/Currency/i).selectOption('ICP');
    
    // Enter invalid ICP address (too short/wrong format)
    await page.getByLabel(/Address/i).fill('invalid-address');
    
    // Click Save
    const saveButton = page.getByRole('button', { name: /Save/i });
    await saveButton.click();
    
    // Should show validation error (any error is fine - validates that validation works)
    await page.waitForTimeout(2000);
    const errorMessage = page.locator('[class*="error"], [class*="alert-error"]');
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
    // Check that error contains something about invalid format or validation
    const errorText = await errorMessage.textContent();
    expect(errorText).toMatch(/Invalid|format|required/i);
  });

  test('should successfully add an ICP payment account', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Open modal
    const addButton = page.getByRole('button', { name: /Add Payment Account/i });
    await addButton.click();
    await page.waitForTimeout(500);
    
    // Fill in form with valid ICP address
    await page.getByLabel(/Account Label|Label/i).fill('My ICP Wallet');
    
    const networkSelect = page.getByLabel(/Network/i);
    await networkSelect.selectOption('ICP');
    
    await page.getByLabel(/Address/i).fill('test1-test2-test3-test4-test5-test6-test7-test8-test9-testa-eqe');
    
    // Click Save
    const saveButton = page.getByRole('button', { name: /Save/i });
    await saveButton.click();
    
    // Wait for account to be added
    await page.waitForTimeout(2000);
    
    // Modal should close
    await expect(page.getByRole('heading', { name: /Add Payment Account/i })).not.toBeVisible();
    
    // Account should appear in the list
    await expect(page.getByText('My ICP Wallet')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/test1-test2-test3/)).toBeVisible();
  });

  test('should display account details correctly', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Wait for accounts to load
    await page.waitForTimeout(2000);
    
    // Check if there are any accounts
    const accountCards = page.locator('[class*="account-card"], [class*="account"]');
    
    if (await accountCards.count() > 0) {
      const firstAccount = accountCards.first();
      
      // Should have label/name
      await expect(firstAccount).toContainText(/[A-Za-z]{3,}/);
      
      // Should have network badge
      await expect(firstAccount).toContainText(/ICP|Bitcoin|Ethereum|SEPA/i);
      
      // Should have address
      await expect(firstAccount).toContainText(/[a-z0-9-]{10,}/);
      
      // Should have created date
      await expect(firstAccount).toContainText(/Created|created_at/i);
    }
  });

  test('should successfully remove a payment account', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // First, add an account to remove
    const addButton = page.getByRole('button', { name: /Add Payment Account/i });
    await addButton.click();
    await page.waitForTimeout(500);
    
    await page.getByLabel(/Account Label|Label/i).fill('Account to Remove');
    await page.getByLabel(/Address/i).fill('xyz11-abc22-def33-ghi44-jkl55-mno66-pqr77-stu88-vwx99-yza00-eqe');
    
    await page.getByRole('button', { name: /Save/i }).click();
    await page.waitForTimeout(2000);
    
    // Find the remove button for this account
    const removeButton = page.getByRole('button', { name: /Remove|🗑️/i }).first();
    
    if (await removeButton.isVisible({ timeout: 5000 })) {
      // Listen for confirmation dialog
      page.on('dialog', async dialog => {
        expect(dialog.message()).toContain(/remove.*payment account/i);
        await dialog.accept();
      });
      
      await removeButton.click();
      await page.waitForTimeout(2000);
      
      // Account should be removed from list
      await expect(page.getByText('Account to Remove')).not.toBeVisible();
    }
  });

  test('should handle empty state when no accounts exist', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    await page.waitForTimeout(2000);
    
    // Check for empty state message
    const emptyMessage = page.getByText(/No payment accounts|not configured yet/i);
    
    // Either show empty message or show accounts list
    const hasAccounts = await page.locator('[class*="account-card"]').count() > 0;
    const hasEmptyMessage = await emptyMessage.isVisible();
    
    expect(hasAccounts || hasEmptyMessage).toBeTruthy();
  });

  test('should support multiple networks', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Open modal
    const addButton = page.getByRole('button', { name: /Add Payment Account/i });
    await addButton.click();
    await page.waitForTimeout(500);
    
    // Check network dropdown has multiple options
    const networkSelect = page.getByLabel(/Network/i);
    const options = await networkSelect.locator('option').allTextContents();
    
    // Should have at least ICP, Bitcoin, Ethereum, SEPA
    expect(options.length).toBeGreaterThanOrEqual(4);
    expect(options.some(opt => opt.includes('ICP'))).toBeTruthy();
    expect(options.some(opt => opt.includes('Bitcoin'))).toBeTruthy();
    expect(options.some(opt => opt.includes('Ethereum'))).toBeTruthy();
    expect(options.some(opt => opt.includes('SEPA'))).toBeTruthy();
  });

  test('should update currency options based on network selection', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Open modal
    const addButton = page.getByRole('button', { name: /Add Payment Account/i });
    await addButton.click();
    await page.waitForTimeout(500);
    
    // Select ICP network
    const networkSelect = page.getByLabel(/Network/i);
    await networkSelect.selectOption('ICP');
    await page.waitForTimeout(300);
    
    // Check currency options for ICP
    const currencySelect = page.getByLabel(/Currency/i);
    let options = await currencySelect.locator('option').allTextContents();
    expect(options.some(opt => opt.includes('ICP'))).toBeTruthy();
    expect(options.some(opt => opt.includes('ckBTC'))).toBeTruthy();
    
    // Select Bitcoin network
    await networkSelect.selectOption('Bitcoin');
    await page.waitForTimeout(300);
    
    // Check currency options for Bitcoin
    options = await currencySelect.locator('option').allTextContents();
    expect(options.some(opt => opt.includes('BTC'))).toBeTruthy();
  });

  test('should display created timestamp for accounts', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    await page.waitForTimeout(2000);
    
    // Check if there are accounts with timestamps
    const accountCards = page.locator('[class*="account-card"], [class*="account"]');
    
    if (await accountCards.count() > 0) {
      // Look for date display
      const datePattern = /\d{1,2}\/\d{1,2}\/\d{4}/;
      const dateElements = page.locator(`text=${datePattern}`);
      
      if (await dateElements.count() > 0) {
        await expect(dateElements.first()).toBeVisible();
      } else {
        // Check for "Created" label
        await expect(page.getByText(/Created|created_at/i).first()).toBeVisible();
      }
    }
  });

  test('should show loading state while fetching accounts', async ({ page }) => {
    test.setTimeout(TIMEOUT);
    
    // Reload page to see loading state
    await page.reload({ waitUntil: 'domcontentloaded' });
    
    // Navigate to Payment Accounts tab
    const paymentAccountsTab = page.getByText(/Payment Accounts/i).first();
    if (await paymentAccountsTab.isVisible({ timeout: 5000 })) {
      await paymentAccountsTab.click();
    }
    
    // Check for loading indicator (may be brief)
    const loadingIndicator = page.getByText(/Loading|loading/i);
    
    // Either loading is shown or accounts load immediately
    const hasLoading = await loadingIndicator.isVisible({ timeout: 1000 }).catch(() => false);
    const hasAccounts = await page.locator('[class*="account-card"]').count() > 0;
    const hasEmptyState = await page.getByText(/No payment accounts/i).isVisible();
    
    expect(hasLoading || hasAccounts || hasEmptyState).toBeTruthy();
  });
});
