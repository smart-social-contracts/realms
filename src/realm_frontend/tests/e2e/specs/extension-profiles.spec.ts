import { test, expect } from '@playwright/test';
import { AuthHelper } from '../fixtures/auth-helper';
import { SidebarPage } from '../fixtures/sidebar';

const TIMEOUT = 30000;

declare global {
	interface Window {
		__setProfilesForTesting: (profiles: string[]) => Promise<void>;
	}
}

async function setupProfileState(page: any, profiles: string[]) {
	await page.addInitScript((profiles) => {
		window.__setTestProfiles = profiles;
	}, profiles);
}

test.describe('Extension Profile Filtering', () => {
	let authHelper: AuthHelper;
	let sidebarPage: SidebarPage;

	test.beforeEach(async ({ page }) => {
		authHelper = new AuthHelper(page);
		sidebarPage = new SidebarPage(page);
		
		await authHelper.setupAuthenticatedSession();
		
		await page.addInitScript(() => {
			window.__setProfilesForTesting = async (profiles) => {
				const maxAttempts = 50;
				let attempts = 0;
				
				while (attempts < maxAttempts) {
					try {
						const module = await import('/src/lib/stores/profiles.ts');
						if (module.setProfilesForTesting) {
							module.setProfilesForTesting(profiles);
							console.log('Profiles set for testing:', profiles);
							return;
						}
					} catch (e) {
					}
					await new Promise(resolve => setTimeout(resolve, 100));
					attempts++;
				}
				console.error('Failed to set profiles for testing after', maxAttempts, 'attempts');
			};
		});
	});

	test('should show correct extensions for users with no profile', async ({ page }) => {
		test.setTimeout(TIMEOUT);
		
		await page.goto('/dashboard');
		await page.waitForLoadState('networkidle');
		
		await page.evaluate(async () => {
			await window.__setProfilesForTesting([]);
		});
		
		await page.reload();
		await page.waitForLoadState('networkidle');
		await sidebarPage.waitForSidebarToLoad();
		
		const publicExtensions = [
			'AI Assistant',
			'Public Dashboard'
		];
		
		const restrictedExtensions = [
			'Citizen Dashboard',
			'Justice Litigation', 
			'Land Registry',
			'Budget Metrics',
			'Notifications',
			'wallet solid Vault Manager',
			'Extensions Marketplace'
		];
		
		for (const extension of publicExtensions) {
			await expect(page.getByRole('link', { name: new RegExp(extension, 'i') })).toBeVisible({ timeout: 5000 });
		}
		
		for (const extension of restrictedExtensions) {
			await expect(page.getByRole('link', { name: new RegExp(extension, 'i') })).not.toBeVisible();
		}
	});

	test('should show correct extensions for users with member profile', async ({ page }) => {
		test.setTimeout(TIMEOUT);
		
		await page.goto('/dashboard');
		await page.waitForLoadState('networkidle');
		
		await page.evaluate(async () => {
			await window.__setProfilesForTesting(['member']);
		});
		
		await page.reload();
		await page.waitForLoadState('networkidle');
		await sidebarPage.waitForSidebarToLoad();
		
		const memberExtensions = [
			'AI Assistant',
			'Public Dashboard',
			'Citizen Dashboard',
			'Justice Litigation',
			'Land Registry', 
			'Budget Metrics',
			'Notifications'
		];
		
		const adminOnlyExtensions = [
			'wallet solid Vault Manager',
			'Extensions Marketplace'
		];
		
		for (const extension of memberExtensions) {
			await expect(page.getByRole('link', { name: new RegExp(extension, 'i') })).toBeVisible({ timeout: 5000 });
		}
		
		for (const extension of adminOnlyExtensions) {
			await expect(page.getByRole('link', { name: new RegExp(extension, 'i') })).not.toBeVisible();
		}
	});

	test('should show all extensions for users with admin profile', async ({ page }) => {
		test.setTimeout(TIMEOUT);
		
		await page.goto('/dashboard');
		await page.waitForLoadState('networkidle');
		
		await page.evaluate(async () => {
			await window.__setProfilesForTesting(['admin']);
		});
		
		await page.reload();
		await page.waitForLoadState('networkidle');
		await sidebarPage.waitForSidebarToLoad();
		const allExtensions = [
			'AI Assistant',
			'Public Dashboard',
			'Citizen Dashboard',
			'Justice Litigation',
			'Land Registry',
			'Budget Metrics',
			'Notifications',
			'wallet solid Vault Manager',
			'Extensions Marketplace'
		];
		
		for (const extension of allExtensions) {
			await expect(page.getByRole('link', { name: new RegExp(extension, 'i') })).toBeVisible({ timeout: 5000 });
		}
	});

	test('should show correct extensions for users with both member and admin profiles', async ({ page }) => {
		test.setTimeout(TIMEOUT);
		
		await page.goto('/dashboard');
		await page.waitForLoadState('networkidle');
		
		await page.evaluate(async () => {
			await window.__setProfilesForTesting(['member', 'admin']);
		});
		
		await page.reload();
		await page.waitForLoadState('networkidle');
		await sidebarPage.waitForSidebarToLoad();
		const allExtensions = [
			'AI Assistant',
			'Public Dashboard',
			'Citizen Dashboard',
			'Justice Litigation',
			'Land Registry',
			'Budget Metrics',
			'Notifications',
			'wallet solid Vault Manager',
			'Extensions Marketplace'
		];
		
		for (const extension of allExtensions) {
			await expect(page.getByRole('link', { name: new RegExp(extension, 'i') })).toBeVisible({ timeout: 5000 });
		}
	});
});
