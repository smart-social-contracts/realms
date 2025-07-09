import { test, expect } from '@playwright/test';

test.describe('Basic Navigation', () => {
	test('should load dashboard page directly', async ({ page }) => {
		await page.goto('/dashboard');
		await page.waitForLoadState('networkidle');
		
		await expect(page.locator('body')).toBeVisible();
		await expect(page.locator('html')).not.toContainText('404');
	});

	test('should load extensions marketplace directly', async ({ page }) => {
		await page.goto('/extensions');
		await page.waitForLoadState('networkidle');
		
		await expect(page.locator('body')).toBeVisible();
		await expect(page.locator('html')).not.toContainText('404');
	});

	test('should load individual extension pages directly', async ({ page }) => {
		const extensionPages = [
			'/extensions/citizen_dashboard',
			'/extensions/justice_litigation',
			'/extensions/land_registry',
			'/extensions/ai_assistant',
			'/extensions/budget_metrics',
			'/extensions/notifications',
			'/extensions/public_dashboard',
			'/extensions/test_bench',
			'/extensions/vault_manager'
		];

		for (const extensionPath of extensionPages) {
			await test.step(`Load ${extensionPath}`, async () => {
				await page.goto(extensionPath);
				await page.waitForLoadState('networkidle');
				
				await expect(page.locator('body')).toBeVisible();
				await expect(page.locator('html')).not.toContainText('404');
			});
		}
	});

	test('should have working Internet Identity login flow initiation', async ({ page }) => {
		await page.goto('/join');
		await page.waitForLoadState('networkidle');
		
		const loginButton = page.getByRole('link', { name: 'Log in' });
		await expect(loginButton).toBeVisible();
		
	});
});
