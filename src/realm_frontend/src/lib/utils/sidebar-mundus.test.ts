import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
const sidebarPath = resolve(here, '../../routes/(sidebar)/Sidebar.svelte');
const foldPath = resolve(here, '../../routes/(sidebar)/SidebarFold.svelte');
const sidebar = readFileSync(sidebarPath, 'utf8');
const fold = readFileSync(foldPath, 'utf8');

describe('MY MUNDUS super-category styling', () => {
	it('uses the shared gray pill toggle for MY MUNDUS', () => {
		expect(fold).toContain('bg-gray-100');

		const mundusFolds = [
			...sidebar.matchAll(
				/<SidebarFold\s+bind:open=\{foldOpen\['__section_mundus__'\]\}[\s\S]*?<\/SidebarFold>/g,
			),
		];
		expect(mundusFolds.length).toBeGreaterThanOrEqual(2);

		for (const match of mundusFolds) {
			expect(match[0]).not.toContain('summaryClass');
			expect(match[0]).not.toContain('group/cat');
		}
	});

	it('renders MY MUNDUS as a sibling of MY REALM, not nested inside it', () => {
		const mundusDesktop = sidebar.lastIndexOf('<!-- MY MUNDUS section (super-category) -->');
		const realmDesktopClose = sidebar.lastIndexOf("setFoldOpen('__section_realm__'");
		expect(mundusDesktop).toBeGreaterThan(realmDesktopClose);

		const inRealmBlock = sidebar.slice(
			sidebar.indexOf('const inRealm ='),
			sidebar.indexOf('if (inRealm)'),
		);
		expect(inRealmBlock).not.toContain('mundusItems');
	});
});
