import { test, expect } from '@playwright/test';

/**
 * E2E coverage for the package_manager extension — admin UI for installing,
 * updating and uninstalling runtime extensions and codex packages from the
 * realm frontend.
 */
test.describe('Package Manager extension', () => {
	test('shows sign-in gate or manager tabs at /extensions/package_manager', async ({ page }) => {
		test.setTimeout(30_000);

		const consoleErrors: string[] = [];
		page.on('console', (msg) => {
			if (msg.type() === 'error') consoleErrors.push(msg.text());
		});
		page.on('pageerror', (err) => {
			consoleErrors.push(err.message);
		});

		await page.goto('/extensions/package_manager', { waitUntil: 'domcontentloaded' });

		await expect(
			page.getByRole('heading', { name: /Package Manager/i }),
		).toBeVisible({ timeout: 15_000 });

		const signInGate = page.getByRole('button', { name: /^Sign in$/i });
		const installedTab = page.getByRole('tab', { name: /Installed/i });
		const availableTab = page.getByRole('tab', { name: /Available/i });
		const advancedTab = page.getByRole('tab', { name: /Advanced/i });

		if (await signInGate.isVisible()) {
			await expect(signInGate).toBeVisible();
		} else {
			await expect(installedTab).toBeVisible();
			await expect(availableTab).toBeVisible();
			await expect(advancedTab).toBeVisible();
		}

		const newPageErrors = consoleErrors.filter(
			(e) => /package_manager|file-registry-client|PackageManager/.test(e),
		);
		expect(newPageErrors, 'no package-manager-specific console errors').toEqual([]);
	});
});
