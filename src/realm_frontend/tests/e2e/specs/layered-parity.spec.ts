import fs from 'node:fs';
import path from 'node:path';
import { test, expect, type Page } from '@playwright/test';

/**
 * Layered Realm parity snapshots — Issue #168.
 *
 * Goal
 * ----
 * Prove that a Dominion realm using the layered install strategy
 * (`install_strategy: layered`, all 20 extensions + the dominion codex
 * loaded from file_registry at runtime, base WASM with zero bundled
 * extensions) renders pixel-equivalent UI to the legacy bundled deployment.
 *
 * The same spec is meant to be run against TWO targets:
 *
 *   1. The bundled deployment        → produces the *baseline* snapshots.
 *   2. The layered deployment        → must match those baselines (within
 *                                       Playwright's default tolerance).
 *
 * The two runs are correlated by `process.env.PLAYWRIGHT_PARITY_RUN`:
 *
 *   PLAYWRIGHT_PARITY_RUN=baseline  npx playwright test specs/layered-parity \
 *       --update-snapshots
 *
 *   PLAYWRIGHT_PARITY_RUN=layered   npx playwright test specs/layered-parity
 *
 * Snapshots from "baseline" are committed; the "layered" run compares
 * against those baselines. A diverging pixel diff fails the build, which is
 * exactly the gate we want before flipping any production realm to layered.
 *
 * Required env vars (when running against a real deployment):
 *   PLAYWRIGHT_BASE_URL         — http(s) URL where realm_frontend is served
 *
 * Optional env vars:
 *   PLAYWRIGHT_PARITY_RUN       — 'baseline' (default) | 'layered'
 *   PLAYWRIGHT_PARITY_LOCALES   — comma list, default 'en'
 *   PLAYWRIGHT_PARITY_EXT_FILE  — JSON file overriding the default ext list
 *
 * Skipping
 * --------
 * Tests skip cleanly if PLAYWRIGHT_BASE_URL is not set, so this file is
 * safe to keep in the suite without breaking unrelated CI runs.
 */

interface ExtensionUnderTest {
	id: string;
	name: string;
	sidebar_label: Record<string, string>;
	url_path: string | null;
	show_in_sidebar: boolean;
}

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL;
const PARITY_RUN = (process.env.PLAYWRIGHT_PARITY_RUN || 'baseline') as
	| 'baseline'
	| 'layered';
const LOCALES = (process.env.PLAYWRIGHT_PARITY_LOCALES || 'en')
	.split(',')
	.map((s) => s.trim())
	.filter(Boolean);

/**
 * Resolve the canonical list of extensions under test from the
 * realms-extensions/ working copy.  Falls back to a hard-coded list if
 * the working copy is not present (e.g. when tests run from a tarball).
 *
 * Reading from disk keeps the test in sync with the manifest changes
 * landed by `scripts/add_sidebar_labels.py` without manual updates here.
 */
function loadExtensions(): ExtensionUnderTest[] {
	const override = process.env.PLAYWRIGHT_PARITY_EXT_FILE;
	if (override) {
		const json = JSON.parse(fs.readFileSync(override, 'utf-8'));
		return json as ExtensionUnderTest[];
	}

	// realms-extensions/ lives next to realms/ in the developer worktree.
	const repoRoot = path.resolve(__dirname, '..', '..', '..', '..', '..', '..');
	const extDir = path.join(repoRoot, 'realms-extensions', 'extensions');
	if (!fs.existsSync(extDir)) {
		return FALLBACK_EXTENSIONS;
	}

	const out: ExtensionUnderTest[] = [];
	for (const entry of fs.readdirSync(extDir).sort()) {
		const manifestPath = path.join(extDir, entry, 'manifest.json');
		if (!fs.existsSync(manifestPath)) continue;
		try {
			const m = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
			out.push({
				id: m.name ?? entry,
				name: m.name ?? entry,
				sidebar_label:
					typeof m.sidebar_label === 'object' && m.sidebar_label
						? m.sidebar_label
						: { en: m.name ?? entry },
				url_path: m.url_path ?? null,
				show_in_sidebar: m.show_in_sidebar !== false,
			});
		} catch {
			// Tolerate broken/missing manifests; better to skip than to crash.
		}
	}
	return out.length > 0 ? out : FALLBACK_EXTENSIONS;
}

/** Hard-coded mirror of the 20 dominion extensions, used when the
 * realms-extensions/ tree is not co-located. Order matches `ls` of the
 * extensions directory. Sidebar labels match scripts/add_sidebar_labels.py. */
const FALLBACK_EXTENSIONS: ExtensionUnderTest[] = [
	{ id: 'admin_dashboard',     name: 'admin_dashboard',     url_path: 'admin', show_in_sidebar: true,  sidebar_label: { en: 'Admin Dashboard' } },
	{ id: 'codex_viewer',        name: 'codex_viewer',        url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Codex Viewer' } },
	{ id: 'erd_explorer',        name: 'erd_explorer',        url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'ERD Explorer' } },
	{ id: 'hello_world',         name: 'hello_world',         url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Hello World' } },
	{ id: 'justice_litigation',  name: 'justice_litigation',  url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Justice & Litigation' } },
	{ id: 'land_registry',       name: 'land_registry',       url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Land Registry' } },
	{ id: 'llm_chat',            name: 'llm_chat',            url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'AI Assistant' } },
	{ id: 'market_place',        name: 'market_place',        url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Extensions Marketplace' } },
	{ id: 'member_dashboard',    name: 'member_dashboard',    url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'My Dashboard' } },
	{ id: 'metrics',             name: 'metrics',             url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Metrics' } },
	{ id: 'notifications',       name: 'notifications',       url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Notifications' } },
	{ id: 'passport_verification', name: 'passport_verification', url_path: null, show_in_sidebar: true, sidebar_label: { en: 'Passport Verification' } },
	{ id: 'public_dashboard',    name: 'public_dashboard',    url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Public Dashboard' } },
	{ id: 'system_info',         name: 'system_info',         url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'System Info' } },
	{ id: 'task_monitor',        name: 'task_monitor',        url_path: 'monitor', show_in_sidebar: true, sidebar_label: { en: 'Task Monitor' } },
	{ id: 'test_bench',          name: 'test_bench',          url_path: null,    show_in_sidebar: false, sidebar_label: { en: 'Test Bench' } },
	{ id: 'vault',               name: 'vault',               url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Treasury Vault' } },
	{ id: 'voting',              name: 'voting',              url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Voting' } },
	{ id: 'welcome',             name: 'welcome',             url_path: null,    show_in_sidebar: false, sidebar_label: { en: 'Welcome' } },
	{ id: 'zone_selector',       name: 'zone_selector',       url_path: null,    show_in_sidebar: true,  sidebar_label: { en: 'Zone Selector' } },
];

const EXTENSIONS = loadExtensions();

function urlForExtension(ext: ExtensionUnderTest): string {
	return ext.url_path ? `/${ext.url_path}` : `/extensions/${ext.id}`;
}

async function setLocale(page: Page, locale: string): Promise<void> {
	// Sidebar.svelte uses localStorage `preferredLocale` and the document
	// `lang` attribute. Setting both before navigation gives a deterministic
	// rendering regardless of the browser's Accept-Language.
	await page.addInitScript((loc) => {
		try {
			localStorage.setItem('preferredLocale', loc);
			document.documentElement.lang = loc;
		} catch {
			/* localStorage may not be ready in some contexts */
		}
	}, locale);
}

async function disableNoiseForSnapshot(page: Page): Promise<void> {
	// Pause CSS animations / transitions and freeze the caret to keep
	// snapshots stable across runs.
	await page.addStyleTag({
		content: `
			*, *::before, *::after {
				animation-duration: 0s !important;
				animation-delay: 0s !important;
				transition-duration: 0s !important;
				transition-delay: 0s !important;
				caret-color: transparent !important;
			}
		`,
	});
}

test.describe(`Layered/Bundled UI parity (run=${PARITY_RUN})`, () => {
	test.skip(
		!BASE_URL,
		'PLAYWRIGHT_BASE_URL must be set (point to the bundled or layered deployment).',
	);

	test.beforeEach(async ({ page }) => {
		// Cap waits at the slow side of "fast enough"; runtime mounts can
		// take a beat on cold loads, but we don't want flaky CI either.
		page.setDefaultTimeout(30_000);
	});

	for (const locale of LOCALES) {
		test(`sidebar snapshot — locale ${locale}`, async ({ page }, testInfo) => {
			await setLocale(page, locale);
			await page.goto('/', { waitUntil: 'networkidle' });
			await disableNoiseForSnapshot(page);

			// The sidebar is a fixed aside; snapshot just that element so
			// any unrelated header/avatar churn doesn't perturb the diff.
			const aside = page.locator('aside.fixed').first();
			await expect(aside).toBeVisible();

			// Make sure every visible-by-policy extension's label is present.
			for (const ext of EXTENSIONS) {
				if (!ext.show_in_sidebar) continue;
				const expected = ext.sidebar_label[locale] ?? ext.sidebar_label.en ?? ext.name;
				// Label comparison is loose: many labels are short ("Voting"),
				// so we anchor on a substring within the sidebar.
				await expect(aside).toContainText(expected, { timeout: 15_000 });
			}

			testInfo.annotations.push({ type: 'parity-run', description: PARITY_RUN });
			expect(await aside.screenshot()).toMatchSnapshot(
				`sidebar-${locale}.png`,
				{ maxDiffPixelRatio: 0.02 },
			);
		});
	}

	for (const ext of EXTENSIONS) {
		test(`extension page — ${ext.id}`, async ({ page }, testInfo) => {
			await setLocale(page, LOCALES[0] ?? 'en');
			await page.goto(urlForExtension(ext), { waitUntil: 'domcontentloaded' });

			// The new runtime-loaded bundles all render a "(runtime-loaded)"
			// marker; the legacy bundled UIs do not. We don't assert that
			// marker here because this spec must be locale-AND-mode neutral.
			// Instead we just wait for the page to finish loading and ensure
			// the host shell didn't surface an error.
			await page.waitForLoadState('networkidle');
			await disableNoiseForSnapshot(page);

			const body = page.locator('body');
			await expect(body).toBeVisible();
			await expect(body).not.toContainText('Application error', { timeout: 5_000 });
			await expect(body).not.toContainText('404 — Page not found', { timeout: 5_000 });

			testInfo.annotations.push({ type: 'parity-run', description: PARITY_RUN });
			expect(await page.screenshot({ fullPage: true })).toMatchSnapshot(
				`ext-${ext.id}.png`,
				{ maxDiffPixelRatio: 0.04 },
			);
		});
	}
});
