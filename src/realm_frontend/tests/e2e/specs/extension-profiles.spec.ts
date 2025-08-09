import { test, expect } from '@playwright/test';
import { SidebarPage } from '../fixtures/sidebar';

const TIMEOUT = 30000;

test.describe('Extension Profile Filtering', () => {
	let sidebarPage: SidebarPage;

	test.beforeEach(async ({ page }) => {
		sidebarPage = new SidebarPage(page);
	});

	test('should show only public extensions when not logged in', async ({ page }) => {
		test.setTimeout(TIMEOUT);
		
		await page.goto('/dashboard');
		await page.waitForLoadState('networkidle');
		await sidebarPage.waitForSidebarToLoad();
		
		const sidebarLinks = await page.locator('nav a').allTextContents();
		console.log('Sidebar links found when not logged in:', sidebarLinks);
		
		const expectedPublicExtensions = [
			'AI Assistant',
			'Public Dashboard'
		];
		
		for (const extension of expectedPublicExtensions) {
			await expect(page.getByRole('link', { name: new RegExp(extension, 'i') })).toBeVisible({ timeout: 5000 });
		}
		
		const restrictedExtensions = [
			'Citizen Dashboard',
			'Justice Litigation', 
			'Land Registry',
			'Budget Metrics',
			'Notifications',
			'Passport Verification',
			'Vault Manager'
		];
		
		for (const extension of restrictedExtensions) {
			await expect(page.getByRole('link', { name: new RegExp(extension, 'i') })).not.toBeVisible();
		}
	});

});
