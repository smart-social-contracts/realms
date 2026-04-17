import { test, expect } from '@playwright/test';

/**
 * End-to-end verification for Issue #168 — runtime-loaded extension frontends.
 *
 * This proves the dynamic-loader path: realm_frontend fetches an ESM bundle
 * from file_registry over HTTP at runtime, mounts it, and that bundle can
 * then make inter-canister calls back through the injected realm_backend actor.
 *
 * Requires canisters file_registry / realm_backend / realm_frontend to be deployed
 * locally via `bash scripts/test_runtime_frontend_extension.sh` first. The test
 * then connects to the realm_frontend asset canister over localhost:4943.
 *
 * Env vars:
 *   REALM_FRONTEND_CANISTER_ID   — canister id of realm_frontend (required)
 *   FILE_REGISTRY_CANISTER_ID    — canister id of file_registry (required)
 */

const FE_ID = process.env.REALM_FRONTEND_CANISTER_ID;
const REG_ID = process.env.FILE_REGISTRY_CANISTER_ID;

test.describe('Runtime-loaded extension frontend', () => {
	test.skip(!FE_ID || !REG_ID, 'REALM_FRONTEND_CANISTER_ID / FILE_REGISTRY_CANISTER_ID not set');

	test('fetches and mounts the ESM bundle from file_registry', async ({ page }) => {
		const bundleUrl = `http://${REG_ID}.localhost:4943/ext/test_bench/0.1.3/frontend/dist/index.js`;
		const extUrl = `http://${FE_ID}.localhost:4943/extensions/test_bench`;

		const networkRequests: { url: string; status: number; contentType?: string }[] = [];
		page.on('response', async (resp) => {
			const url = resp.url();
			if (url.includes('/ext/test_bench/0.1.3/frontend/dist/index.js')) {
				networkRequests.push({
					url,
					status: resp.status(),
					contentType: resp.headers()['content-type'],
				});
			}
		});

		const consoleErrors: string[] = [];
		page.on('console', (msg) => {
			if (msg.type() === 'error') consoleErrors.push(msg.text());
		});
		page.on('pageerror', (err) => {
			consoleErrors.push(err.message);
		});

		await page.goto(extUrl, { waitUntil: 'domcontentloaded' });

		await expect(page.getByRole('heading', { name: 'Extension: test_bench' })).toBeVisible({
			timeout: 20_000,
		});

		// Real Svelte 5 component compiled by vite --lib mounts the UI.
		// Stable text markers from realms-extensions/extensions/test_bench/frontend-rt/src/Testbench.svelte:
		await expect(page.getByText('(runtime-loaded)')).toBeVisible({ timeout: 20_000 });
		await expect(page.getByText('v0.1.3')).toBeVisible();
		await expect(page.getByRole('button', { name: /extension_sync_call/ })).toBeVisible();

		// Network request to the bundle must have happened with correct MIME.
		expect(networkRequests.length, 'expected GET for runtime extension bundle').toBeGreaterThan(0);
		const bundleResp = networkRequests.find((r) =>
			r.url.includes('/ext/test_bench/0.1.3/frontend/dist/index.js'),
		);
		expect(bundleResp, `bundle request at ${bundleUrl}`).toBeTruthy();
		expect(bundleResp!.status).toBe(200);
		expect(bundleResp!.contentType ?? '').toMatch(/javascript/);

		// Click the bundle's button and verify it round-trips through realm_backend.
		await page.getByRole('button', { name: /extension_sync_call/ }).click();

		const pre = page.locator('pre.output');
		// The runtime-loaded bundle must make a real inter-canister call. We accept
		// two outcomes that both prove the call reached realm_backend:
		//   (a) success  → "some data from runtime-loaded frontend bundle"
		//   (b) anonymous-user permission denial → "extension.sync_call"
		// (The Playwright harness visits the page without completing Internet
		// Identity login, so the anonymous principal is expected.)
		await expect(pre).toContainText(
			/(some data from runtime-loaded frontend bundle|extension\.sync_call|extension_sync_call)/,
			{ timeout: 30_000 },
		);

		// Ignore console errors that are pre-existing frontend issues unrelated
		// to the runtime-loader prototype (e.g. svelte-i18n timing warnings).
		const loaderErrors = consoleErrors.filter(
			(e) =>
				/mountExtension|extension-loader|Failed to fetch dynamically|CANISTER_ID_FILE_REGISTRY/.test(
					e,
				),
		);
		expect(loaderErrors, 'no loader-related console errors').toEqual([]);
	});
});
