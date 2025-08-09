import { test, expect } from '@playwright/test';
import { AuthHelper } from '../fixtures/auth-helper';
import { SidebarPage } from '../fixtures/sidebar';

const TIMEOUT = 30000;

test.describe('Extension Profile Filtering', () => {
	let authHelper: AuthHelper;
	let sidebarPage: SidebarPage;

	test.beforeEach(async ({ page }) => {
		authHelper = new AuthHelper(page);
		sidebarPage = new SidebarPage(page);
		
		await authHelper.setupAuthenticatedSession();
	});

	test('should show sidebar extensions correctly', async ({ page }) => {
		test.setTimeout(TIMEOUT);
		
		await page.goto('/dashboard');
		await page.waitForLoadState('networkidle');
		await sidebarPage.waitForSidebarToLoad();
		
		await page.evaluate(async () => {
			try {
				const profilesModule = await import('/src/lib/stores/profiles.ts');
				console.log('Profile store module:', Object.keys(profilesModule));
				
				profilesModule.setProfilesForTesting([]);
				console.log('Set profiles to empty array');
				
				window.dispatchEvent(new CustomEvent('profilesChanged', { detail: { profiles: [] } }));
				console.log('Dispatched profilesChanged event');
				
				const { userProfiles } = profilesModule;
				console.log('Current userProfiles store:', userProfiles);
				
			} catch (error) {
				console.error('Error manipulating profiles:', error);
			}
		});
		
		await page.waitForTimeout(1000);
		
		await page.screenshot({ path: 'test-results/sidebar-screenshot.png', fullPage: true });
		
		const sidebarLinks = await page.locator('nav a').allTextContents();
		console.log('Sidebar links found:', sidebarLinks);
		
		const expectedPublicExtensions = [
			'AI Assistant',
			'Public Dashboard'
		];
		
		for (const extension of expectedPublicExtensions) {
			const linkExists = await page.getByRole('link', { name: new RegExp(extension, 'i') }).count() > 0;
			console.log(`Extension "${extension}" found: ${linkExists}`);
		}
		
		expect(sidebarLinks.length).toBeGreaterThan(0);
	});

});
