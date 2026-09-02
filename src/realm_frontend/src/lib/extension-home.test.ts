import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { extensionHref, resolveMemberHomeHref } from './extension-home';

describe('resolveMemberHomeHref', () => {
	it('uses the get_sidebar_manifests My Dashboard row (is_default) and /extensions/[id]', () => {
		expect(
			resolveMemberHomeHref({
				manifests: [
					{ id: 'passport_verification', sidebar_label: { en: 'Passport Verification' } },
					{ id: 'civic_home', sidebar_label: { en: 'My Dashboard' }, is_default: true },
				],
			}),
		).toBe('/extensions/civic_home');
	});

	it('matches the painted My Dashboard sidebar_label when is_default is absent', () => {
		expect(
			resolveMemberHomeHref({
				manifests: [{ id: 'home_ext', sidebar_label: { de: 'My Dashboard' } }],
				locale: 'de',
			}),
		).toBe('/extensions/home_ext');
	});

	it('falls back to the first MY REALM welcome item', () => {
		expect(
			resolveMemberHomeHref({
				manifests: [{ id: 'voting', sidebar_label: { en: 'Voting' } }],
				welcomeItems: [{ extension_id: 'first_realm', href: '/extensions/first_realm', label: 'Start' }],
			}),
		).toBe('/extensions/first_realm');
	});

	it('falls back to realm home when no MY REALM row exists', () => {
		expect(resolveMemberHomeHref({ manifests: [], welcomeItems: [] })).toBe('/');
		expect(resolveMemberHomeHref(null)).toBe('/');
	});

	it('never hardcodes a dashboard extension id', () => {
		expect(extensionHref('any_installed_id')).toBe('/extensions/any_installed_id');
		expect(resolveMemberHomeHref.toString()).not.toMatch(/member_dashboard/);
		expect(extensionHref.toString()).not.toMatch(/member_dashboard/);
	});

	it('is re-exported next to the extension loader and [id] route', () => {
		const dir = dirname(fileURLToPath(import.meta.url));
		const loader = readFileSync(join(dir, 'extension-loader.ts'), 'utf8');
		expect(loader).toContain('resolveMemberHomeHref');
		expect(loader).toContain('./extension-home');
		const page = readFileSync(
			join(dir, '../routes/(sidebar)/extensions/[id]/+page.svelte'),
			'utf8',
		);
		expect(page).toContain('ExtensionRoutePage');
		const route = readFileSync(join(dir, 'components/ExtensionRoutePage.svelte'), 'utf8');
		expect(route).toContain('{#key id}');
		expect(route).toContain('isMemberInboxExtension');
		expect(route).toContain('MEMBER_INBOX_HREF');
	});
});
