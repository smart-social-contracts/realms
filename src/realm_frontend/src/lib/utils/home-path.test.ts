import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { resolveHomePath } from './home-path';

describe('resolveHomePath', () => {
	it('resolves /extensions/[id] from get_sidebar_manifests', () => {
		expect(
			resolveHomePath({
				manifests: [{ id: 'civic_home', sidebar_label: { en: 'My Dashboard' }, is_default: true }],
			}),
		).toBe('/extensions/civic_home');
	});

	it('falls back to the first MY REALM item, then realm home', () => {
		expect(
			resolveHomePath({
				welcomeItems: [{ extensionId: 'first_realm', href: '/extensions/first_realm' }],
			}),
		).toBe('/extensions/first_realm');
		expect(resolveHomePath(null)).toBe('/extensions/public_dashboard');
	});

	it('is what the sidebar layout uses for navigate.home', () => {
		const layout = readFileSync(
			join(dirname(fileURLToPath(import.meta.url)), '../../routes/(sidebar)/+layout.svelte'),
			'utf8',
		);
		expect(layout).toContain('navigate.home');
		expect(layout).toContain('resolveHomePath');
		expect(layout).toContain('sidebarConfig');
		expect(layout).toContain('get_sidebar_manifests');
	});
});
