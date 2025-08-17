import { Page, expect } from '@playwright/test';

export class SidebarPage {
	constructor(private page: Page) {}

	async navigateToPage(pageName: string) {
		switch (pageName) {
			case 'Dashboard':
				await this.page.getByRole('link', { name: 'Dashboard' }).click();
				break;
			case 'My Identities':
				await this.page.getByRole('link', { name: 'My Identities' }).click();
				break;
			case 'Admin Dashboard':
				await this.page.getByRole('link', { name: 'Admin Dashboard' }).click();
				break;
			case 'Settings':
				await this.page.getByRole('link', { name: 'Settings' }).click();
				break;
			case 'Extensions Marketplace':
				await this.page.getByRole('link', { name: 'Extensions Marketplace' }).click();
				break;
			case 'Citizen Dashboard':
			case 'Justice Litigation':
			case 'Land Registry':
			case 'AI Assistance':
			case 'Budget Metrics':
			case 'Notifications':
			case 'Public Dashboard':
			case 'test_bench':
			case 'Vault Manager':
				const extensionsDropdown = this.page.getByRole('button', { name: 'Extensions' });
				if (await extensionsDropdown.isVisible()) {
					await extensionsDropdown.click();
				}
				await this.page.getByRole('link', { name: pageName }).click();
				break;
			default:
				throw new Error(`Unknown page: ${pageName}`);
		}
	}

	async verifyPageLoaded(expectedTitle?: string) {
		await this.page.waitForLoadState('networkidle', { timeout: 30000 });
		await expect(this.page.locator('body')).not.toContainText('Error', { timeout: 10000 });
		
		if (expectedTitle) {
			await expect(this.page).toHaveTitle(new RegExp(expectedTitle, 'i'));
		}
	}

	async waitForSidebarToLoad() {
		await expect(this.page.getByRole('complementary', { name: 'Sidebar' })).toBeVisible();
		await this.page.waitForTimeout(1000);
	}

	async expandExtensionsIfNeeded() {
		const extensionsButton = this.page.getByRole('button', { name: 'Extensions' });
		if (await extensionsButton.isVisible()) {
			const isExpanded = await extensionsButton.getAttribute('aria-expanded');
			if (isExpanded !== 'true') {
				await extensionsButton.click();
				await this.page.waitForTimeout(500);
			}
		}
	}
}
