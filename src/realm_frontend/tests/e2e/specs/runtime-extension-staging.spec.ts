import { test, expect } from '@playwright/test';

/**
 * Staging smoke test for Issue #168 — runtime-loaded extension frontends.
 *
 * Verifies that the Dominion realm on staging dynamically loads the
 * test_bench ESM bundle from the file_registry canister and mounts it.
 *
 * Env vars:
 *   STAGING_FRONTEND_URL — e.g. https://iocgc-oaaaa-aaaac-beh2q-cai.icp0.io
 *   STAGING_REGISTRY_ID  — e.g. iebdk-kqaaa-aaaau-agoxq-cai
 */

const FE_URL = process.env.STAGING_FRONTEND_URL;
const REG_ID = process.env.STAGING_REGISTRY_ID;

test.describe('Staging runtime-loaded extension', () => {
	test.skip(
		!FE_URL || !REG_ID,
		'STAGING_FRONTEND_URL / STAGING_REGISTRY_ID must be set',
	);

	test('Dominion frontend dynamically loads test_bench from file_registry', async ({
		page,
	}) => {
		const extUrl = `${FE_URL}/extensions/test_bench`;
		const bundlePath = '/ext/test_bench/0.1.3/frontend/dist/index.js';

		const bundleResponses: { url: string; status: number; contentType?: string }[] = [];
		page.on('response', async (resp) => {
			const url = resp.url();
			if (url.includes(bundlePath)) {
				bundleResponses.push({
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
		page.on('pageerror', (err) => consoleErrors.push(err.message));

		await page.goto(extUrl, { waitUntil: 'domcontentloaded' });

		// The runtime-loaded bundle must mount within a reasonable window.
		await expect(page.getByText('(runtime-loaded)')).toBeVisible({ timeout: 40_000 });
		await expect(page.getByText('v0.1.3')).toBeVisible();
		await expect(page.getByRole('button', { name: /extension_sync_call/ })).toBeVisible();

		expect(bundleResponses.length, 'expected GET for bundle').toBeGreaterThan(0);
		const hit = bundleResponses.find((r) => r.url.includes(`${REG_ID}.`));
		expect(hit, `bundle should come from ${REG_ID}`).toBeTruthy();
		expect(hit!.status).toBe(200);
		expect(hit!.contentType ?? '').toMatch(/javascript/);

		// Click the bundle's button and verify it round-trips through realm_backend.
		await page.getByRole('button', { name: /extension_sync_call/ }).click();

		const pre = page.locator('pre.output');
		await expect(pre).toContainText(
			/(some data from runtime-loaded frontend bundle|extension\.sync_call|extension_sync_call|Access denied|success|error)/,
			{ timeout: 40_000 },
		);

		// Any CSP/fetch/loader errors specific to the runtime-loader fail the test.
		const loaderErrors = consoleErrors.filter((e) =>
			/Refused to (load|execute)|mountExtension|extension-loader|Failed to fetch dynamically/.test(
				e,
			),
		);
		expect(loaderErrors, `no CSP / loader errors; got:\n${loaderErrors.join('\n')}`).toEqual(
			[],
		);
	});
});
