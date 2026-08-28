import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
	PLATFORM_PLACEHOLDER_LOGOS,
	REALM_CUSTOM_LOGO,
	isPlatformPlaceholderLogo,
	resolveRealmMarkSrc
} from './realmMark';

const here = dirname(fileURLToPath(import.meta.url));
const navbar = readFileSync(resolve(here, '../../routes/(sidebar)/Navbar.svelte'), 'utf8');
const appHtml = readFileSync(resolve(here, '../../app.html'), 'utf8');

describe('resolveRealmMarkSrc', () => {
	it('uses the same-origin custom mark before backend logo_url arrives', () => {
		expect(resolveRealmMarkSrc('')).toBe(REALM_CUSTOM_LOGO);
		expect(resolveRealmMarkSrc(null)).toBe(REALM_CUSTOM_LOGO);
		expect(resolveRealmMarkSrc(undefined)).toBe(REALM_CUSTOM_LOGO);
	});

	it('keeps a real branding URL once loaded', () => {
		expect(resolveRealmMarkSrc('/custom/logo.png')).toBe('/custom/logo.png');
		expect(resolveRealmMarkSrc('https://assets.example/realm.png')).toBe(
			'https://assets.example/realm.png'
		);
	});

	it('never resolves the GOS planet or retired clover', () => {
		for (const placeholder of PLATFORM_PLACEHOLDER_LOGOS) {
			expect(isPlatformPlaceholderLogo(placeholder)).toBe(true);
			expect(resolveRealmMarkSrc(placeholder)).toBe(REALM_CUSTOM_LOGO);
			expect(resolveRealmMarkSrc(`${placeholder}?v=2`)).toBe(REALM_CUSTOM_LOGO);
		}
	});
});

describe('live realm chrome', () => {
	it('does not default the header or favicon to the planet or clover', () => {
		expect(navbar).toContain('resolveRealmMarkSrc');
		expect(navbar).not.toContain('logo_sphere_only');
		expect(navbar).not.toContain('/images/logo.png');
		expect(appHtml).toContain('href="/custom/logo.png"');
		expect(appHtml).not.toContain('href="/images/logo.png"');
		expect(appHtml).not.toContain('logo_sphere_only');
	});

	it('does not ship default /custom brand files in the frontend asset tree', () => {
		const customDir = resolve(here, '../../../static/custom');
		expect(existsSync(resolve(customDir, 'logo.png'))).toBe(false);
		expect(existsSync(resolve(customDir, 'background.png'))).toBe(false);
		expect(existsSync(resolve(here, '../../../static/images/logo.png'))).toBe(true);
		expect(existsSync(resolve(here, '../../../static/images/background.png'))).toBe(true);
	});
});
