import { test, expect } from '@playwright/test';
import { AuthHelper } from '../fixtures/auth-helper';
import { SidebarPage } from '../fixtures/sidebar';
import { time } from 'console';

const TIMEOUT = 300000;

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
		test.setTimeout(TIMEOUT);


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
		await expect(savedAndContinueButton).toBeVisible({ timeout: TIMEOUT });
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

		// await page.waitForLoadState('networkidle');
		await expect(page.getByText('Successfully Joined!')).toBeVisible({ timeout: TIMEOUT });

		await page.getByRole('button', { name: 'Go to Dashboard' }).click();
		
		// await page.waitForLoadState('networkidle');
		await expect(page.getByRole('complementary', { name: 'Sidebar' })).toBeVisible({ timeout: TIMEOUT });

		// await page.getByRole('button', { name: 'objects column outline' }).click();

		const links = [
			{ name: 'users outline My Identities' , needle: 'Manage and connect your' },
			{ name: 'table column solid Admin' , needle: 'Generalized Global Governance System' },
			{ name: 'cog outline Settings' , needle: 'Principal:' },
			{ name: 'Extensions Marketplace' , needle: 'Browse and install' },
			{ name: 'wallet solid Vault Manager' , needle: 'Vault Configuration' },
			{ name: 'Citizen Dashboard' , needle: 'Dashboard Overview' },
			{ name: 'Justice Litigation' , needle: 'Justice Litigation System' },
			{ name: 'Land Registry' , needle: 'Manage land ownership' },
			{ name: 'AI Assistant' , needle: 'Governance AI assistant' },
			{ name: 'Budget Metrics' , needle: 'Tax Allocation Breakdown' },
			{ name: 'Notifications' , needle: 'unread notifications' },
			{ name: 'Public Dashboard' , needle: 'Active users on the platform' }
		];

		for (const link of links) {
			// await page.getByRole('button', { name: 'objects column outline' }).click(); // expand Extensions sidebar
			await page.getByRole('link', { name: link.name }).click();
			// await page.waitForLoadState('networkidle', { timeout: TIMEOUT });
			await expect(page.getByRole('complementary', { name: 'Sidebar' })).toBeVisible({ timeout: TIMEOUT });
			if (link.needle) {
				await expect(page.getByText(link.needle)).toBeVisible({ timeout: TIMEOUT });
			}
		}



	});

	test('should navigate to home page when logo is clicked', async ({ page }) => {
		test.setTimeout(TIMEOUT);
		
		await page.setViewportSize({ width: 1200, height: 800 }); // Ensure desktop view
		await page.goto('/');
		await page.waitForLoadState('networkidle');
		
		await page.goto('/join');
		await page.waitForLoadState('networkidle');
		
		const logoLink = page.getByRole('link').filter({ has: page.getByAltText('Smart Social Contracts Logo') });
		await expect(logoLink).toBeVisible();
		await logoLink.click();
		
		await page.waitForLoadState('networkidle');
		await expect(page).toHaveURL('/');
		
		const loginButton = page.getByRole('button', { name: 'Log In' });
		await expect(loginButton).toBeVisible();
	});	
});
