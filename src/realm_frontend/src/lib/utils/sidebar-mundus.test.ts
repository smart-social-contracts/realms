import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const sidebarPath = resolve(
	dirname(fileURLToPath(import.meta.url)),
	'../../routes/(sidebar)/Sidebar.svelte',
);
const source = readFileSync(sidebarPath, 'utf8');

describe('MY MUNDUS super-category styling', () => {
	it('uses the shared gray pill toggle for MY MUNDUS', () => {
		expect(source).toContain("const SECTION_TOGGLE_CLASSES =");
		expect(source).toContain('bg-gray-100');

		const mundusToggleMatches = [
			...source.matchAll(/toggleCategory\('__section_mundus__'\)/g),
		];
		expect(mundusToggleMatches.length).toBeGreaterThanOrEqual(2);

		// Both mobile and desktop Mundus headers sit on the shared gray pill class.
		const mundusBlocks = source.split("toggleCategory('__section_mundus__')");
		// Every mundus toggle except the trailing remainder should be preceded by SECTION_TOGGLE_CLASSES
		for (let i = 0; i < mundusBlocks.length - 1; i++) {
			expect(mundusBlocks[i]).toContain('SECTION_TOGGLE_CLASSES');
		}
	});

	it('renders MY MUNDUS as a sibling of MY REALM, not nested inside it', () => {
		const realmClose = source.lastIndexOf("collapsedCategories.has('__section_realm__')");
		const mundusDesktop = source.lastIndexOf('<!-- MY MUNDUS section (super-category) -->');
		expect(mundusDesktop).toBeGreaterThan(realmClose);
	});
});
