import { test, expect } from '@playwright/test';
import { AuthHelper } from '../fixtures/auth-helper';
import { SidebarPage } from '../fixtures/sidebar';
import { time } from 'console';

test.describe('User workflows', () => {
	let authHelper: AuthHelper;
	let sidebarPage: SidebarPage;

	// test.beforeEach(async ({ page }) => {
	// 	authHelper = new AuthHelper(page);
	// 	sidebarPage = new SidebarPage(page);
		
	// 	await authHelper.navigateToAuthenticatedApp();
	// 	await sidebarPage.waitForSidebarToLoad();
	// });

	test('should be able to become admin', async ({ page }) => {
		const context = page.context();

		await page.goto('/');
		await page.waitForLoadState('networkidle');
		
		const loginButton = page.getByRole('button', { name: 'Log In' });
		await expect(loginButton).toBeVisible();
		
		// Wait for the new popup window to open
		const [internetIdentityPage] = await Promise.all([
			page.context().waitForEvent('page'),        // wait for popup
			page.click('button:has-text("Log In")'),     // click triggers popup
		]);

		// Ensure the popup has loaded
		await internetIdentityPage.waitForLoadState();

		// Optional: check if it's the Internet Identity service
		expect(internetIdentityPage.url()).toContain('authorize');

		// Wait for navigation to the Internet Identity page
		await internetIdentityPage.waitForNavigation({ waitUntil: 'networkidle' });
		
		// Now look for the "More options" link on the Internet Identity page
		const createIdentityButton = internetIdentityPage.getByRole('button', { name: 'Create Internet Identity' });
		await expect(createIdentityButton).toBeVisible();
		await createIdentityButton.click();

		await internetIdentityPage.waitForLoadState('networkidle');
		// "Prove you're not a robot"
		const proveYouAreNotARobot = internetIdentityPage.getByRole('heading', { name: 'Prove you\'re not a robot' });
		await expect(proveYouAreNotARobot).toBeVisible();

		const typeTheCharactersYouSee = internetIdentityPage.getByRole('textbox', { name: 'Type the characters you see' });
		await expect(typeTheCharactersYouSee).toBeVisible();

		await typeTheCharactersYouSee.fill('a');
		await internetIdentityPage.getByRole('button', { name: 'Next' }).click();
		
		await internetIdentityPage.waitForLoadState('networkidle');

		const savedAndContinueButton = internetIdentityPage.getByRole('button', { name: 'I saved it, continue' });
		await expect(savedAndContinueButton).toBeVisible({ timeout: 10000 });
		await savedAndContinueButton.click();
		
		// Wait for the tab to close after login
		while (!internetIdentityPage.isClosed()) {
			try {
				await internetIdentityPage.waitForTimeout(100); // poll every 100ms
			} catch (e) {
				// ignore
				break;
			}
		}

		// const newPage = await context.newPage()
		// await newPage.goto('/');
		// await newPage.waitForLoadState('networkidle');
		
		await page.goto('/');
		await page.waitForLoadState('networkidle');
		const joinButton = page.getByRole('button', { name: 'Join' });
		await expect(joinButton).toBeVisible();
		await joinButton.click();
		
		await page.waitForLoadState('networkidle');

		

		const selectProfileType = page.getByRole('combobox');
		await expect(selectProfileType).toBeVisible();
		await selectProfileType.selectOption('Administrator');

		await page.getByRole('radio', { name: 'I agree to the terms' }).click();
		

		await page.getByRole('button', { name: 'Join Realm as admin' }).click();

		await page.waitForLoadState('networkidle');
		await expect(page.getByText('Successfully Joined!')).toBeVisible();

		await page.getByRole('button', { name: 'Go to Dashboard' }).click();
		
		await page.waitForLoadState('networkidle');
		await expect(page.getByRole('complementary', { name: 'Sidebar' })).toBeVisible({ timeout: 10000 });

		await page.getByRole('button', { name: 'objects column outline' }).click();

		const links = [
			{ name: 'users outline My identities' },
			{ name: 'table column solid Admin' },
			{ name: 'cog outline Settings' },
			{ name: 'layers solid Extensions' },
			{ name: 'wallet solid Vault Manager' },
			{ name: 'Citizen Dashboard' },
			{ name: 'Justice Litigation' },
			{ name: 'Land Registry' },
			{ name: 'AI assistant' },
			{ name: 'Budget Metrics' },
			{ name: 'Notifications' },
			{ name: 'Public Dashboard' },
			{ name: 'layers solid Extensions' },
			{ name: 'wallet solid Vault Manager' },
		];

		for (const link of links) {
			await page.getByRole('link', { name: link.name }).click();
			await page.waitForLoadState('networkidle');
			await expect(page.getByRole('complementary', { name: 'Sidebar' })).toBeVisible({ timeout: 10000 });
		}



	});	
});
