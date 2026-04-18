import { test, expect } from '@playwright/test';

/**
 * E2E coverage for the package_manager extension — admin UI for installing,
 * updating and uninstalling runtime extensions and codex packages from the
 * realm frontend.
 *
 * What this verifies (without requiring a fully wired admin login):
 *   - The page renders and registers in the SvelteKit router under
 *     `/extensions/package_manager` (i.e. the source extension was
 *     installed into realm_frontend).
 *   - The three tabs (Installed / Browse / Upload) are present.
 *
 * The richer install/uninstall round-trip (which requires an authenticated
 * admin principal and a populated file_registry) is left to the existing
 * `runtime-extension.spec.ts` infrastructure; this spec only asserts that
 * the new UI is reachable and structurally correct.
 */
test.describe('Package Manager extension', () => {
	test('renders the three tabs at /extensions/package_manager', async ({ page }) => {
		test.setTimeout(30_000);

		const consoleErrors: string[] = [];
		page.on('console', (msg) => {
			if (msg.type() === 'error') consoleErrors.push(msg.text());
		});
		page.on('pageerror', (err) => {
			consoleErrors.push(err.message);
		});

		await page.goto('/extensions/package_manager', { waitUntil: 'domcontentloaded' });

		// Title — comes from the en.json bundled with the extension.
		await expect(
			page.getByRole('heading', { name: /Package Manager/i }),
		).toBeVisible({ timeout: 15_000 });

		// All three tabs must be rendered. We use a regex match because
		// translations may add extra whitespace / decorations.
		await expect(page.getByRole('tab', { name: /Installed/i })).toBeVisible();
		await expect(page.getByRole('tab', { name: /Browse/i })).toBeVisible();
		await expect(page.getByRole('tab', { name: /Upload/i })).toBeVisible();

		// No frontend regressions specific to this page (we ignore
		// pre-existing svelte-i18n / network warnings).
		const newPageErrors = consoleErrors.filter(
			(e) => /package_manager|file-registry-client|PackageManager/.test(e),
		);
		expect(newPageErrors, 'no package-manager-specific console errors').toEqual([]);
	});
});
