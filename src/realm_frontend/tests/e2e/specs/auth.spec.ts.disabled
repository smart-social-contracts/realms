import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
	test('should display join page correctly', async ({ page }) => {
		await page.goto('/join');
		await page.waitForLoadState('networkidle');
		
		await expect(page.getByRole('heading', { name: 'Join Realm' })).toBeVisible();
		await expect(page.getByText('Do you agree to these terms?')).toBeVisible();
		await expect(page.getByText('Select Profile Type')).toBeVisible();
		
		await expect(page.locator('input[name="agreement"][value="agree"]')).toBeVisible();
		await expect(page.locator('select')).toBeVisible();
		await expect(page.locator('button[type="submit"]')).toBeVisible();
	});

	test('should show authentication requirement', async ({ page }) => {
		await page.goto('/join');
		await page.waitForLoadState('networkidle');
		
		await expect(page.getByText('You must be logged in to join this Realm. Please log in first and then return to this page.')).toBeVisible();
	});

	test('should have working form interactions', async ({ page }) => {
		await page.goto('/join');
		await page.waitForLoadState('networkidle');
		
		const agreeRadio = page.locator('input[name="agreement"][value="agree"]');
		const profileSelect = page.locator('select');
		const submitButton = page.locator('button[type="submit"]');
		
		await expect(agreeRadio).toBeVisible();
		await expect(profileSelect).toBeVisible();
		await expect(submitButton).toBeVisible();
		
		await agreeRadio.click();
		await expect(agreeRadio).toBeChecked();
		
		await profileSelect.selectOption('admin');
		await expect(profileSelect).toHaveValue('admin');
	});
});
