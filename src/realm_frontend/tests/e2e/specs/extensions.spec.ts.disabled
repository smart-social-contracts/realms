import { test, expect } from '@playwright/test';
import { AuthHelper } from '../fixtures/auth-helper';
import { SidebarPage } from '../fixtures/sidebar';

test.describe('Extensions System', () => {
	let authHelper: AuthHelper;
	let sidebarPage: SidebarPage;

	test.beforeEach(async ({ page }) => {
		authHelper = new AuthHelper(page);
		sidebarPage = new SidebarPage(page);
		
		await authHelper.mockInternetIdentity();
		await authHelper.mockBackendCalls();
		await authHelper.loginAsAdmin();
		await sidebarPage.waitForSidebarToLoad();
	});

	test('should load Extensions Marketplace', async ({ page }) => {
		await sidebarPage.navigateToPage('Extensions Marketplace');
		await expect(page.getByText('Extensions Marketplace')).toBeVisible();
		await expect(page.getByText('Browse and install extensions')).toBeVisible();
	});

	test('should navigate through all extension pages', async ({ page }) => {
		const extensionPages = [
			'Citizen Dashboard',
			'Justice Litigation', 
			'Land Registry',
			'AI assistant',
			'Budget Metrics',
			'Notifications',
			'Public Dashboard',
			'test_bench',
			'Vault Manager'
		];

		for (const extensionName of extensionPages) {
			await test.step(`Test ${extensionName} extension`, async () => {
				await sidebarPage.expandExtensionsIfNeeded();
				await sidebarPage.navigateToPage(extensionName);
				await sidebarPage.verifyPageLoaded();
				await expect(page.locator('main')).toBeVisible();
			});
		}
	});

	test('should handle extension dropdown interaction', async ({ page }) => {
		const extensionsButton = page.getByRole('button', { name: 'Extensions' });
		
		if (await extensionsButton.isVisible()) {
			await extensionsButton.click();
			
			await expect(page.getByRole('link', { name: 'Vault Manager' })).toBeVisible();
			await expect(page.getByRole('link', { name: 'Public Dashboard' })).toBeVisible();
		}
	});
});
